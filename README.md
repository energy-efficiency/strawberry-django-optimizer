# strawberry-django-optimizer

[![PyPI version](https://img.shields.io/pypi/v/strawberry-django-optimizer.svg)](https://pypi.org/project/strawberry-django-optimizer/)
![python version](https://img.shields.io/pypi/pyversions/strawberry-django-optimizer.svg)
![django version](https://img.shields.io/pypi/djversions/strawberry-django-optimizer.svg)

Optimize queries executed by [strawberry](https://github.com/strawberry-graphql/strawberry) automatically,
using [`select_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-related)
, [`prefetch_related`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#prefetch-related)
and [`only`](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#only) methods of Django QuerySet.

This package is heavily based on [graphene-django-optimizer](https://github.com/tfoxy/graphene-django-optimizer) which is intended for use with  [graphene-django](https://github.com/graphql-python/graphene-django).

## Install

```bash
pip install strawberry-django-optimizer
```

## Usage

Having the following models based on
the [strawberry-graphql-django](https://github.com/strawberry-graphql/strawberry-graphql-django) docs:

```py
# models.py
from django.db import models


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey('Color', blank=True, null=True,
                              related_name='fruits', on_delete=models.CASCADE)


class Color(models.Model):
    name = models.CharField(max_length=20)

```

And the following schema:

```py
# schema.py
import strawberry
from typing import List
from strawberry.django import auto
from strawberry_django_optimizer import optimized_django_field
from fruits import models


@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: 'Color'


@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]


@strawberry.type
class Query:
    fruits: List[Fruit] = optimized_django_field()
```

The following graphql query would cause n + 1 DB queries:

```graphql
query Fruit {
    fruits {
        id
        name
        color {
            id
            name
        }
    }
}
```

Since `optimized_django_field` was used instead of `strawberry.django.field` the queryset is automatically optimized.

```py
# optimized queryset:
Fruits.objects.select_related('color').only('id', 'name', 'color__id', 'color__name')
```

Reverse `ForeignKey` relations also are automatically optimized with `prefetch_related`:
```graphql
query Colors {
    colors {
        id
        name
        fruits {
            id
            name
        }
    }
}
```

```py
# optimized queryset:
Color.objects.only('id', 'name', 'color').prefetch_related(
    Prefetch('fruits', queryset=Fruit.objects.only('id', 'name'))
)
```

## Advances usage

Use `resolver_hint` for cases where `only`, `select_related` and `prefetch_related` optimizations can't be inferred automatically.
To keep the `only` when using resolver functions `resolver_hints` must be used to declare all fields that are accessed
or the `only` optimization will be disabled. 
```py
# schema.py
import strawberry
from strawberry.django import auto
from strawberry_django_optimizer import resolver_hints
from fruits import models


@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    
    @resolver_hints(only=('name',))
    @strawberry.field
    def name_display(self) -> str:
        return f'My name is: {self.name}'
```

```py
# schema.py
import strawberry
from strawberry.django import auto
from strawberry_django_optimizer import resolver_hints
from fruits import models


@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    
    @resolver_hints(
        select_related=('color',),
        only=('color__name',),
    )
    def color_display(self) -> str:
        return f'My color is: {self.color.name}'

```

### Parameters for `resolver_hint`

| Parameter          | Usage                                         |
| ------------------ | --------------------------------------------- |
| `model_field`      | If the resolver returns a model field         |
| `only`             | Declare all fields that the resolver accesses |
| `select_related`   | If the resolver uses related fields           |
| `prefetch_realted` | If the resolver uses related fields           |

## Known issues (ToDo)

- Inline Fragments can't be optimized
- Interfaces and Unions are not supported