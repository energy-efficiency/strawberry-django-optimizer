import logging
from django.db.models import ForeignKey, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP

_logger = logging.getLogger(__name__)


class QueryOptimizerStore:
    """
    Store for Django QuerySet optimizations.
    """

    def __init__(self, disable_abort_only=False):
        self.select_list = []
        self.prefetch_list = []
        self.only_list = []
        self.disable_abort_only = disable_abort_only

    def select_related(self, name, store: 'QueryOptimizerStore'):
        if store.select_list:
            for select in store.select_list:
                self.select_list.append(name + LOOKUP_SEP + select)
        else:
            self.select_list.append(name)
        for prefetch in store.prefetch_list:
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(name)
            else:
                prefetch = name + LOOKUP_SEP + prefetch
            self.prefetch_list.append(prefetch)
        if self.only_list is not None:
            if store.only_list is None:
                self.abort_only_optimization()
            else:
                for only in store.only_list:
                    self.only_list.append(name + LOOKUP_SEP + only)

    def prefetch_related(self, name, store: 'QueryOptimizerStore', queryset):
        _logger.info('prefetch_related %r %r %r %r', name, store.select_list, store.only_list, store.prefetch_list)
        if store.select_list or store.only_list:
            queryset = store.optimize_queryset(queryset)
            self.prefetch_list.append(Prefetch(name, queryset=queryset))
        elif store.prefetch_list:
            for prefetch in store.prefetch_list:
                if isinstance(prefetch, Prefetch):
                    prefetch.add_prefix(name)
                else:
                    prefetch = name + LOOKUP_SEP + prefetch
                self.prefetch_list.append(prefetch)
        else:
            self.prefetch_list.append(name)

    def only(self, field):
        if self.only_list is not None:
            self.only_list.append(field)

    def abort_only_optimization(self):
        if not self.disable_abort_only:
            self.only_list = None

    def optimize_queryset(self, queryset):
        if self.select_list:
            queryset = queryset.select_related(*self.select_list)

        if self.prefetch_list:
            queryset = queryset.prefetch_related(*self.prefetch_list)

        if self.only_list:
            queryset = queryset.only(*self.only_list)

        return queryset

    def append(self, store: 'QueryOptimizerStore'):
        self.select_list += store.select_list
        self.prefetch_list += store.prefetch_list
        if self.only_list is not None:
            if store.only_list is None:
                self.only_list = None
            else:
                self.only_list += store.only_list
