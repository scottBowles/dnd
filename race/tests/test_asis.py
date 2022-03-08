import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import AbilityScoreIncreaseFactory
from .utils import CompareMixin


class AbilityScoreIncreaseQueryTests(CompareMixin, GraphQLTestCase):
    def test_asi_detail_query(self):
        asi = AbilityScoreIncreaseFactory()

        response = self.query(
            """
            query {
                abilityScoreIncrease(id: "%s") {
                    id
                    abilityScore
                    increase
                }
            }
            """
            % to_global_id("AbilityScoreIncreaseNode", asi.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_asi = res_json["data"]["abilityScoreIncrease"]

        self.compare_ability_score_increases(asi, res_asi)

    def test_trait_list_query(self):
        asis = AbilityScoreIncreaseFactory.create_batch(random.randint(0, 3))
        asis = list(set(asis))

        response = self.query(
            """
            query {
                abilityScoreIncreases {
                    edges {
                        node {
                            id
                            abilityScore
                            increase
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_asis = res_json["data"]["abilityScoreIncreases"]["edges"]

        self.assertEqual(len(asis), len(res_asis))

        for i, asi in enumerate(asis):
            self.compare_ability_score_increases(asi, res_asis[i]["node"])
