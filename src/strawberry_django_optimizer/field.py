from strawberry.arguments import UNSET
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.resolvers import django_resolver
from strawberry_django.utils import unwrap_type
from .query import optimize_query


class OptimizedStrawberryDjangoField(StrawberryDjangoField):
    def get_queryset(self, queryset, info, **kwargs):
        queryset = super().get_queryset(queryset, info, **kwargs)
        record_type = unwrap_type(self.type)
        return optimize_query(queryset, info=info, gql_type=record_type)


def optimized_django_field(resolver=None, *, name=None, field_name=None, filters=UNSET, default=UNSET, **kwargs):
    field_ = OptimizedStrawberryDjangoField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        filters=filters,
        django_name=field_name,
        default=default,
        **kwargs
    )
    if resolver:
        resolver = django_resolver(resolver)
        return field_(resolver)
    return field_
