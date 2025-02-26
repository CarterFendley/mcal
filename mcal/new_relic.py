from datetime import datetime
from typing import Dict

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from mcal.utils.env_file import load_env_file

DEFAULT_ENDPOINT = "https://api.newrelic.com/graphql"

class NewRelicClient:
    def __init__(
        self,
        account_id: int, # TODO: Multi-account
        api_key: str,
        endpoint: str = DEFAULT_ENDPOINT
    ):
        self.account_id = account_id
        self.api_key = api_key
        self.endpoint = endpoint

        self.client = Client(
            transport=AIOHTTPTransport(
                url=self.endpoint,
                headers={
                    'API-Key': self.api_key
                }
            ),
            fetch_schema_from_transport=True # Note: This is important for sane error messages
        )

    def query(self, query: str):
        # Variable substitution reference: https://gql.readthedocs.io/en/stable/usage/variables.html
        request = gql(
            """
            query ($id: Int!, $query: Nrql!) {
                actor {
                    account(id: $id) {
                        nrql(query: $query) { results }
                    }
                }
            }
            """
        )
        result = self.client.execute(
            request,
            variable_values={
                'id': self.account_id,
                'query': query
            }
        )
        return result["actor"]["account"]["nrql"]["results"]

    def _create_empty_dashboard(self):
        result = self.client.execute(gql(
            """
            mutation {
            dashboardCreate(
                dashboard: {
                    name: "Programmatic!",
                    permissions: PRIVATE,
                    pages: {
                        name: "Main Page",
                        widgets: { configuration: {
                            markdown: {text: "My Empty Widget"}
                        }}
                    }
                }
                accountId: 
            ) {
                errors {
                description
                type
                }
            }
            }
            """
        ))
        print(result)

def client_from_env_file(env_file: str = None) -> NewRelicClient:
    if env_file is not None:
        env = load_env_file(env_file)
    else:
        env = load_env_file()

    return NewRelicClient(
        account_id=env.get_account_id(),
        api_key=env.get_user_key()
    )

if __name__ == '__main__':
    nr = NewRelicClient()
    # nr._create_empty_dashboard()