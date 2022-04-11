import random
from graphql_jwt.testcases import JSONWebTokenTestCase
from graphql_relay import to_global_id
from .factories import ProficiencyFactory
from .utils import CompareMixin
from django.contrib.auth import get_user_model


class ProficiencyTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_proficiency_detail_query(self):
        proficiency = ProficiencyFactory()
        response = self.client.execute(
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
        self.assertIsNone(response.errors)

        res_proficiency = response.data["proficiency"]
        self.compare_proficiencies(proficiency, res_proficiency)

    def test_proficiency_list_query(self):
        num_proficiencies = random.randint(0, 10)
        proficiencies = ProficiencyFactory.create_batch(num_proficiencies)
        response = self.client.execute(
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
        self.assertIsNone(response.errors)
        res_proficiencies = response.data["proficiencies"]["edges"]
        self.assertEqual(len(res_proficiencies), num_proficiencies)
        for i, proficiency in enumerate(proficiencies):
            res_proficiency = res_proficiencies[i]["node"]
            self.compare_proficiencies(proficiency, res_proficiency)
