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
    Fruit.objects.create(name='Pear', color=green)
    Fruit.objects.create(name='Banana', color=yellow)
    Fruit.objects.create(name='Strawberry', color=red)
    Fruit.objects.create(name='Cherry', color=red)
    return Fruit.objects.count(), Color.objects.count()


def test_fruits(client, db_fixture):
    fruit_count, color_count = db_fixture
    query = """
    query Fruits {
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
        assert len(fruits) == fruit_count
        # n + 1 queries
        assert len(connection.queries) == fruit_count + 1


def test_optimized_fruits(client, db_fixture):
    """Test that a list query with a FK relation is optimized with `select_related."""
    fruit_count, color_count = db_fixture
    query = """
    query Fruits {
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
        assert len(fruits) == fruit_count
        assert len(connection.queries) == 1


def test_colors(client, db_fixture):
    fruit_count, color_count = db_fixture
    query = """
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
    """
    with CaptureQueriesContext(connection):
        response = client.post('/graphql/', json.dumps({'query': query}), content_type='application/json')
        colors = response.json()['data']['colors']
        assert len(colors) == color_count
        assert len(connection.queries) == color_count + 1


def test_optimized_colors(client, db_fixture):
    """Test that a list query with a backward FK relation is optimized with `prefetch_related."""
    fruit_count, color_count = db_fixture
    query = """
    query Colors {
        optimizedColors {
            id
            name
            fruits {
                id
                name
            }
        }
    }
    """
    with CaptureQueriesContext(connection):
        response = client.post('/graphql/', json.dumps({'query': query}), content_type='application/json')
        colors = response.json()['data']['optimizedColors']
        assert len(colors) == color_count
        assert len(connection.queries) == 2
