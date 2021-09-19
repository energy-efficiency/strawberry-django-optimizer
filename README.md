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

The following graphql query would produce n + 1 DB queries:

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

Since `optimized_django_field` was used instead of `strawberry.django.field` the queryset was automatically optimized
with `select_related('color')`:

```py
# optimized queryset:
Fruits.objects.select_related('color').only('id', 'name', 'color__id', 'color__name')
```
