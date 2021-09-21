from enum import Enum
from django.db import models


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey('Color', blank=True, null=True,
                              related_name='fruits', on_delete=models.CASCADE)


class StoneType(Enum):
    FREESTONE = 'freestone'
    CLINGSTONE = 'clingstone'
    TRYMA = 'tryma'


class StoneFruit(Fruit):
    stone_type = models.CharField(choices=[(t.value, t.value) for t in StoneType], default=StoneType.FREESTONE.value)


class Color(models.Model):
    name = models.CharField(max_length=20)
