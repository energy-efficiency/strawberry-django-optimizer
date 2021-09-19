from .hints import OptimizationHints
from .utils import noop


def resolver_hints(model_field=None,
                   select_related=noop,
                   prefetch_related=noop,
                   only=noop):
    """
    Decorator that adds optimization hints to resolver functions.
    """
    optimization_hints = OptimizationHints(model_field=model_field, select_related=select_related,
                                           prefetch_related=prefetch_related, only=only)

    def apply_resolver_hints(resolver):
        resolver.optimization_hints = optimization_hints
        return resolver

    return apply_resolver_hints
