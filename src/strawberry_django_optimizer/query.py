import logging
from typing import List
from strawberry.types import Info
from strawberry.types.nodes import Selection
from strawberry.lazy_type import LazyType
from strawberry.types.nodes import SelectedField, FragmentSpread, InlineFragment
from strawberry.utils.str_converters import to_camel_case
from django.core.exceptions import FieldDoesNotExist
from django.db.models import ForeignKey, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields.reverse_related import ManyToOneRel

from graphql import GraphQLSchema
from graphql.type.definition import GraphQLInterfaceType, GraphQLUnionType

from .store import QueryOptimizerStore
from .utils import is_iterable

_logger = logging.getLogger(__name__)


def optimize_query(queryset: QuerySet, info: Info, gql_type, selections: List[Selection] = None, **options):
    """
    Automatically optimize queries.

    Arguments:
        - queryset (Django QuerySet object) - The queryset to be optimized
        - info (GraphQL GraphQLResolveInfo object) - This is passed by the graphene-django resolve methods
        - gql_type
        - **options - optimization options/settings
            - disable_abort_only (boolean) - in case the objecttype contains any extra fields,
                                             then this will keep the "only" optimization enabled.
    """
    if not selections:
        selections = info.selected_fields[0].selections
    return QueryOptimizer(info, **options).optimize(queryset, selections, gql_type)


class QueryOptimizer:
    """
    Automatically optimize queries.
    """

    def __init__(self, info: Info, **options):
        self.root_info = info
        self.disable_abort_only = options.pop('disable_abort_only', False)

    def optimize(self, queryset: QuerySet, selections: List[Selection], gql_type):
        store = self._optimize_gql_selections(selections, gql_type)
        _logger.info('only_list: %r', store.only_list)
        _logger.info('disable_abort_only: %r', store.disable_abort_only)
        _logger.info('select_list: %r', store.select_list)
        _logger.info('prefetch_list: %r', store.prefetch_list)
        return store.optimize_queryset(queryset)

    def _get_type(self, field_def):
        a_type = field_def.type
        while hasattr(a_type, 'of_type'):
            a_type = a_type.of_type
        return a_type

    def _get_graphql_schema(self, schema):
        if isinstance(schema, GraphQLSchema):
            return schema
        else:
            return schema.graphql_schema

    def _get_possible_types(self, graphql_type):
        if isinstance(graphql_type, (GraphQLInterfaceType, GraphQLUnionType)):
            # ToDo
            graphql_schema = self._get_graphql_schema(self.root_info.schema)
            return graphql_schema.get_possible_types(graphql_type)
        else:
            return (graphql_type,)

    def _get_base_model(self, graphql_types):
        models = tuple(t.graphene_type._meta.model for t in graphql_types)
        for model in models:
            if all(issubclass(m, model) for m in models):
                return model
        return None

    def handle_inline_fragment(self, selection, schema, possible_types, store):
        fragment_type_name = selection.type_condition.name.value
        graphql_schema = self._get_graphql_schema(schema)
        fragment_type = graphql_schema.get_type(fragment_type_name)
        fragment_possible_types = self._get_possible_types(fragment_type)
        for fragment_possible_type in fragment_possible_types:
            fragment_model = fragment_possible_type.graphene_type._meta.model
            parent_model = self._get_base_model(possible_types)
            if not parent_model:
                continue
            path_from_parent = fragment_model._meta.get_path_from_parent(parent_model)
            select_related_name = LOOKUP_SEP.join(
                p.join_field.name for p in path_from_parent
            )
            if not select_related_name:
                continue
            fragment_store = self._optimize_gql_selections(
                fragment_possible_type,
                selection,
                # parent_type,
            )
            store.select_related(select_related_name, fragment_store)
        return store

    def _optimize_gql_selections(self, selected_fields: List[SelectedField], graphql_type,
                                 store: QueryOptimizerStore = None) -> QueryOptimizerStore:
        """
        Walk the selected fields (part of the gql query) recursively.
        """
        _logger.info('_optimize_gql_selections %r %r', graphql_type, selected_fields)
        if not store:
            store = QueryOptimizerStore(disable_abort_only=self.disable_abort_only)
        if not selected_fields:
            return store
        optimized_fields_by_model = {}
        # schema = self.root_info.schema
        possible_types = self._get_possible_types(graphql_type)
        for selected_field in selected_fields:
            if isinstance(selected_field, InlineFragment):
                # Inline Fragment e.g. `... on Droid {}`
                # ToDo
                # self.handle_inline_fragment(selected_field, schema, possible_types, store)
                continue
            name = selected_field.name
            if name == '__typename':
                continue
            if type(selected_field) is FragmentSpread:
                self._optimize_gql_selections(selected_field.selections, graphql_type, store=store)
                continue
            for type_ in possible_types:
                if isinstance(type_, LazyType):
                    type_ = type_.resolve_type()
                if selected_field.name == 'rows' and selected_field.selections:
                    # Cursor pagination - optimize the selected fields in `rows`
                    self._optimize_gql_selections(selected_field.selections, graphql_type, store=store)
                    continue
                selection_field_def = next(
                    (field for field in type_._type_definition.fields if to_camel_case(field.name) == name),
                    None)
                if not selection_field_def:
                    continue
                model = type_._django_type.model
                if model and name not in optimized_fields_by_model:
                    optimized_fields_by_model[name] = model
                    self._optimize_field(store, model, selected_field, selection_field_def, type_)
        return store

    def _optimize_field(self, store: QueryOptimizerStore, model, selection, field_def, parent_type):
        optimized_by_name = self._optimize_field_by_name(store, model, selection, field_def)
        optimized_by_hints = self._optimize_field_by_hints(store, selection, field_def)
        if not (optimized_by_name or optimized_by_hints):
            store.abort_only_optimization()

    def _optimize_field_by_name(self, store: QueryOptimizerStore, model, selection, field_def) -> bool:
        """
        Add optimization to the store by inspecting the model field type.
        """
        name = self._get_name_from_field_dev(field_def)
        if not (model_field := self._get_model_field_from_name(model, name)):
            return False
        _logger.info('_optimize_field_by_name %r %r', name, model_field)
        if self._is_foreign_key_id(model_field, name):
            # ToDo: check if this works - i write resolvers for this
            store.only(name)
            return True
        if model_field.many_to_one or model_field.one_to_one:
            # ForeignKey or OneToOneField
            field_store = self._optimize_gql_selections(
                selection.selections,
                self._get_type(field_def),
            )
            store.select_related(name, field_store)
            return True
        if model_field.one_to_many or model_field.many_to_many:
            field_store = self._optimize_gql_selections(
                selection.selections,
                self._get_type(field_def),
            )
            if isinstance(model_field, ManyToOneRel):
                field_store.only(model_field.field.name)
            related_queryset = model_field.related_model.objects.all()
            _logger.info('_optimize_field_by_name many relation %r %r', model, name)
            store.prefetch_related(name, field_store, related_queryset)
            return True
        if not model_field.is_relation:
            store.only(name)
            return True
        return False

    @staticmethod
    def _add_optimization_hints(source, target):
        if source:
            if not is_iterable(source):
                source = (source,)
            target += source

    def _optimize_field_by_hints(self, store: QueryOptimizerStore, selected_field, field_def) -> bool:
        """
        Add the optimizations from the resolver_hints decorator to the store.
        """
        if not (optimization_hints := getattr(field_def, 'optimization_hints', None)):
            return False
        args = selected_field.arguments
        self._add_optimization_hints(optimization_hints.select_related(*args), store.select_list)
        self._add_optimization_hints(optimization_hints.prefetch_related(*args), store.prefetch_list)
        if store.only_list is not None:
            self._add_optimization_hints(optimization_hints.only(*args), store.only_list)
        return True

    def _get_name_from_field_dev(self, field_dev):
        # _logger.info('_get_name_from_field_dev %r', field_dev.name)
        if optimization_hints := getattr(field_dev, 'optimization_hints', None):
            if name_fn := optimization_hints.model_field:
                if (name := name_fn()) is not None:
                    return name
        return field_dev.name
        # if self._is_resolver_for_id_field(resolver):
        #     return 'id'
        # elif isinstance(resolver, functools.partial):
        #     resolver_fn = resolver
        #     if resolver_fn.func != default_resolver:
        #         # Some resolvers have the partial function as the second
        #         # argument.
        #         for arg in resolver_fn.args:
        #             if isinstance(arg, (str, functools.partial)):
        #                 break
        #         else:
        #             # No suitable instances found, default to first arg
        #             arg = resolver_fn.args[0]
        #         resolver_fn = arg
        #     if (
        #         isinstance(resolver_fn, functools.partial)
        #         and resolver_fn.func == default_resolver
        #     ):
        #         return resolver_fn.args[0]
        #     if self._is_resolver_for_id_field(resolver_fn):
        #         return 'id'
        #     return resolver_fn

    def _is_resolver_for_id_field(self, resolver) -> bool:
        resolve_id = DjangoObjectType.resolve_id
        # For python 2 unbound method:
        if hasattr(resolve_id, 'im_func'):
            resolve_id = resolve_id.im_func
        return resolver == resolve_id

    def _get_model_field_from_name(self, model, name: str):
        # _logger.info('_get_model_field_from_name %r %r', model, name)
        if '__' in name:
            name = name.split('__')[0]
        try:
            return model._meta.get_field(name)
        except FieldDoesNotExist:
            if not (descriptor := getattr(model, name, None)):
                return None
            return getattr(descriptor, 'related', None)

    def _is_foreign_key_id(self, model_field, name: str) -> bool:
        return (
            isinstance(model_field, ForeignKey)
            and model_field.name != name
            and model_field.get_attname() == name
        )
