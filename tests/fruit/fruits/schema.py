import strawberry
from strawberry.django import auto
from strawberry_django_optimizer import optimized_django_field
from typing import List
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
    fruits: List[Fruit] = strawberry.django.field()
    optimized_fruits: List[Fruit] = optimized_django_field()
    colors: List[Color] = strawberry.django.field()
    optimized_colors: List[Color] = optimized_django_field()


schema = strawberry.Schema(Query)
