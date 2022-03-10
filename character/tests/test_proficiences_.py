import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import ProficiencyFactory
from .utils import CompareMixin


class ProficiencyTests(CompareMixin, GraphQLTestCase):
    def test_proficiency_detail_query(self):
        proficiency = ProficiencyFactory()
        response = self.query(
            """
            query {
                proficiency(id: "%s") {
                    id
                    name
                    description
                    proficiencyType
                }
            }
            """
            % to_global_id("ProficiencyNode", proficiency.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_proficiency = res_json["data"]["proficiency"]
        self.compare_proficiencies(proficiency, res_proficiency)

    def test_proficiency_list_query(self):
        num_proficiencies = random.randint(0, 10)
        proficiencies = ProficiencyFactory.create_batch(num_proficiencies)
        response = self.query(
            """
            query {
                proficiencies {
                    edges {
                        node {
                            id
                            name
                            description
                            proficiencyType
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)
        res_json = json.loads(response.content)
        res_proficiencies = res_json["data"]["proficiencies"]["edges"]
        self.assertEqual(len(res_proficiencies), num_proficiencies)
        for i, proficiency in enumerate(proficiencies):
            res_proficiency = res_proficiencies[i]["node"]
            self.compare_proficiencies(proficiency, res_proficiency)
