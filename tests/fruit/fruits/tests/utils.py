import json


def query_graphql(client, query: str, variables: dict=None):
    """
    Args:
        query (string)    - GraphQL query to run
        variables (dict)  - If provided, the "variables" field in GraphQL will be
                            set to this value.

    Returns:
        Response object from client
    """
    body = {'query': query}
    if variables:
        body['variables'] = variables
    return client.post('/graphql/', json.dumps(body), content_type='application/json')
