import pytest
from fruits.models import Fruit, Color


@pytest.fixture()
def db_fixture(db):
    red = Color.objects.create(name='Red')
    green = Color.objects.create(name='Green')
    yellow = Color.objects.create(name='Yellow')
    Fruit.objects.create(name='Apple', color=green)
    Fruit.objects.create(name='Pear', color=green)
    Fruit.objects.create(name='Banana', color=yellow)
    Fruit.objects.create(name='Strawberry', color=red)
    Fruit.objects.create(name='Cherry', color=red)
    return Fruit.objects.count(), Color.objects.count()
