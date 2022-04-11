import random
import json
from graphql_jwt.testcases import JSONWebTokenTestCase
from graphql_relay import to_global_id
from .factories import AbilityScoreIncreaseFactory
from .utils import CompareMixin
from character.models.models import ABILITIES
from ..models import AbilityScoreIncrease
from graphql_relay import from_global_id, to_global_id
from django.contrib.auth import get_user_model


class AbilityScoreIncreaseQueryTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_asi_detail_query(self):
        asi = AbilityScoreIncreaseFactory()

        response = self.client.execute(
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
        self.assertIsNone(response.errors)

        res_asi = response.data["abilityScoreIncrease"]

        self.compare_ability_score_increases(asi, res_asi)

    def test_asi_list_query(self):
        asis = AbilityScoreIncreaseFactory.create_batch(random.randint(0, 3))
        asis = list(set(asis))
        asis.sort(key=lambda x: x.id)

        response = self.client.execute(
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
        self.assertIsNone(response.errors)

        res_asis = response.data["abilityScoreIncreases"]["edges"]

        self.assertEqual(len(asis), len(res_asis))

        for i, asi in enumerate(asis):
            self.compare_ability_score_increases(asi, res_asis[i]["node"])


class AbilityScoreIncreaseMutationTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

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

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_asi = response.data["abilityScoreIncreaseCreate"]["abilityScoreIncrease"]

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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

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

        response = self.client.execute(query)

        self.assertIsNotNone(response.errors)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreaseUpdate' on type 'Mutation'",
            response.errors[0].message,
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

        response = self.client.execute(query)

        self.assertIsNotNone(response.errors)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreasePatch' on type 'Mutation'",
            response.errors[0].message,
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

        response = self.client.execute(query)

        self.assertIsNotNone(response.errors)
        self.assertIn(
            "Cannot query field 'abilityScoreIncreaseDelete' on type 'Mutation'",
            response.errors[0].message,
        )
