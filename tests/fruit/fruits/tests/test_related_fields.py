import json
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from .utils import query_graphql
from .fixtures import db_fixture

pytestmark = pytest.mark.django_db


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
        response = query_graphql(client, query)
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
        response = query_graphql(client, query)
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
        response = query_graphql(client, query)
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
        response = query_graphql(client, query)
        colors = response.json()['data']['optimizedColors']
        assert len(colors) == color_count
        assert len(connection.queries) == 2
