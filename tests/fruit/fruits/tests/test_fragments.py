import json
from django.db import connection
from django.test.utils import CaptureQueriesContext
from .utils import query_graphql
from .fixtures import db_fixture


def test_fruit_fragment(client, db_fixture):
    """Test that the fields of a fragment spread can be optimized."""
    fruit_count, color_count = db_fixture
    query = """
    fragment fruit on Fruit {
        id
        name
        color {
            id
            name
        }
    }
    
    query Fruits {
        optimizedFruits {
            ...fruit
        }
    }
    """
    with CaptureQueriesContext(connection):
        response = query_graphql(client, query)
        fruits = response.json()['data']['optimizedFruits']
        assert len(fruits) == fruit_count
        assert len(connection.queries) == 1


def test_color_fragment(client, db_fixture):
    """Test that the fields of a nested fragment spread can be optimized."""
    fruit_count, color_count = db_fixture
    query = """
    fragment color on Color {
        id
        name
    }

    query Fruits {
        optimizedFruits {
            id
            name
            color {
                ...color
            }
        }
    }
    """
    with CaptureQueriesContext(connection):
        response = query_graphql(client, query)
        fruits = response.json()['data']['optimizedFruits']
        assert len(fruits) == fruit_count
        assert len(connection.queries) == 1
        assert 'name' in fruits[0]['color']


def test_inline_fragment(client, db_fixture):
    """Test that the fields of an inline fragment spread can be optimized."""
    fruit_count, color_count = db_fixture
    query = """
    query Fruits {
        optimizedFruits {
            ...on Fruit {
                id
                name
                color {
                    id
                    name
                }
            }
        }
    }
    """
    with CaptureQueriesContext(connection):
        response = query_graphql(client, query)
        fruits = response.json()['data']['optimizedFruits']
        assert len(fruits) == fruit_count
        assert len(connection.queries) == 1
