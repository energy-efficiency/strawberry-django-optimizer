import json
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from fruits.models import Fruit, Color

pytestmark = pytest.mark.django_db


@pytest.fixture()
def db_fixture(db):
    red = Color.objects.create(name='Red')
    green = Color.objects.create(name='Green')
    yellow = Color.objects.create(name='Yellow')
    Fruit.objects.create(name='Apple', color=green)
    Fruit.objects.create(name='Banana', color=yellow)
    Fruit.objects.create(name='Strawberry', color=red)


def test_fruits(client, db_fixture):
    query = """
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
    """

    with CaptureQueriesContext(connection):
        response = client.post('/graphql/', json.dumps({'query': query}), content_type='application/json')
        fruits = response.json()['data']['fruits']
        assert len(fruits) == 3
        # n + 1 queries
        assert len(connection.queries) == len(fruits) + 1


def test_optimized_fruits(client, db_fixture):
    query = """
    query Fruit {
        optimizedFruits {
            id
            name
            color {
                id
                name
            }
        }
    }
    """

    with CaptureQueriesContext(connection):
        response = client.post('/graphql/', json.dumps({'query': query}), content_type='application/json')
        fruits = response.json()['data']['optimizedFruits']
        assert len(fruits) == 3
        assert len(connection.queries) == 1
