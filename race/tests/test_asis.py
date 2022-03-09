import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import AbilityScoreIncreaseFactory
from .utils import CompareMixin
from character.models.models import ABILITIES
from ..models import AbilityScoreIncrease
from graphql_relay import from_global_id, to_global_id


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


class AbilityScoreIncreaseMutationTests(CompareMixin, GraphQLTestCase):
    def test_asi_create_mutation(self):
        ability = random.choice(ABILITIES)[0]
        increase = random.randint(1, 6)
        query = """
            mutation {
                abilityScoreIncreaseCreate(input: {
                    abilityScore: "%s",
                    increase: %s
                }) {
                    ok
                    errors
                    abilityScoreIncrease {
                        id
                        abilityScore
                        increase
                    }
                }
            }
        """ % (
            ability,
            increase,
        )

        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_asi = result["data"]["abilityScoreIncreaseCreate"]["abilityScoreIncrease"]

        self.assertEqual(res_asi["abilityScore"], ability)
        self.assertEqual(res_asi["increase"], increase)

        created_asi = AbilityScoreIncrease.objects.get(
            pk=from_global_id(res_asi["id"])[1]
        )
        self.assertEqual(created_asi.ability_score, ability)
        self.assertEqual(created_asi.increase, increase)

        self.compare_ability_score_increases(created_asi, res_asi)

    def test_asi_create_bad_input(self):
        query = """
            mutation {
                abilityScoreIncreaseCreate(input: {
                    description: "Test asi Description"
                }) {
                    ok
                    errors
                    abilityScoreIncrease {
                        id
                        abilityScore
                        increase
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_asi_update_unavailable(self):
        asi = AbilityScoreIncreaseFactory()
        query = """
            mutation {
                abilityScoreIncreaseUpdate(input: {
                    id: "%s",
                    abilityScore: "STRENGTH",
                    increase: 1
                }) {
                    ok
                    errors
                    abilityScoreIncrease {
                        id
                        abilityScore
                        increase
                    }
                }
            }
        """ % to_global_id(
            "AbilityScoreIncreaseNode", asi.id
        )

        response = self.query(query)
        result = json.loads(response.content)

        self.assertResponseHasErrors(response)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreaseUpdate' on type 'Mutation'",
            result["errors"][0]["message"],
        )

    def test_asi_patch_unavailable(self):
        asi = AbilityScoreIncreaseFactory()
        query = """
            mutation {
                abilityScoreIncreasePatch(input: {
                    id: "%s",
                    increase: 1
                }) {
                    ok
                    errors
                    abilityScoreIncrease {
                        id
                        abilityScore
                        increase
                    }
                }
            }
        """ % to_global_id(
            "AbilityScoreIncreaseNode", asi.id
        )

        response = self.query(query)
        result = json.loads(response.content)

        self.assertResponseHasErrors(response)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreasePatch' on type 'Mutation'",
            result["errors"][0]["message"],
        )

    def test_asi_delete_unavailable(self):
        asi = AbilityScoreIncreaseFactory()
        query = """
            mutation {
                abilityScoreIncreaseDelete(input: {
                    abilityScore: "%s",
                    increase: "%s"
                }) {
                    ok
                    errors
                }
            }
        """ % (
            asi.ability_score,
            asi.increase,
        )

        response = self.query(query)
        result = json.loads(response.content)

        self.assertResponseHasErrors(response)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreaseDelete' on type 'Mutation'",
            result["errors"][0]["message"],
        )
