import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import TraitFactory
from .utils import CompareMixin


class TraitQueryTests(CompareMixin, GraphQLTestCase):
    def test_trait_detail_query(self):
        trait = TraitFactory()

        response = self.query(
            """
            query {
                trait(id: "%s") {
                    id
                    name
                    description
                }
            }
            """
            % to_global_id("TraitNode", trait.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_trait = res_json["data"]["trait"]

        self.compare_traits(trait, res_trait)

    def test_trait_list_query(self):
        traits = TraitFactory.create_batch(random.randint(0, 3))

        response = self.query(
            """
            query {
                traits {
                    edges {
                        node {
                            id
                            name
                            description
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_traits = res_json["data"]["traits"]["edges"]

        for i, trait in enumerate(traits):
            self.compare_traits(trait, res_traits[i]["node"])
