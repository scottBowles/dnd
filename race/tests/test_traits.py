import random
import json
from graphql_jwt.testcases import JSONWebTokenTestCase
from graphql_relay import from_global_id, to_global_id
from .factories import TraitFactory
from .utils import CompareMixin
from ..models import Trait
from django.contrib.auth import get_user_model


class TraitQueryTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_trait_detail_query(self):
        trait = TraitFactory()

        response = self.client.execute(
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

        self.assertIsNone(response.errors)
        res_trait = response.data["trait"]
        self.compare_traits(trait, res_trait)

    def test_trait_list_query(self):
        traits = TraitFactory.create_batch(random.randint(0, 3))

        response = self.client.execute(
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
        self.assertIsNone(response.errors)

        res_traits = response.data["traits"]["edges"]

        for i, trait in enumerate(traits):
            self.compare_traits(trait, res_traits[i]["node"])


class TraitMutationTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_trait_create_mutation(self):
        name = "Test Trait Name"
        description = "Test Trait Description"
        query = """
            mutation {
                traitCreate(input: {
                    name: "%s",
                    description: "%s"
                }) {
                    ok
                    errors
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """ % (
            name,
            description,
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_trait = response.data["traitCreate"]["trait"]

        self.assertEqual(res_trait["name"], name)
        self.assertEqual(res_trait["description"], description)

        created_trait = Trait.objects.get(pk=from_global_id(res_trait["id"])[1])
        self.assertEqual(created_trait.name, name)
        self.assertEqual(created_trait.description, description)

        self.compare_traits(created_trait, res_trait)

    def test_trait_create_bad_input(self):
        query = """
            mutation {
                traitCreate(input: {
                    description: "Test trait Description"
                }) {
                    ok
                    errors
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_trait_update_mutation(self):
        trait = TraitFactory(
            name="Not Test Trait Name", description="Not Test Trait Description"
        )
        trait_global_id = to_global_id("TraitNode", trait.id)
        query = (
            """
            mutation {
                traitUpdate(input: {
                    id: "%s"
                    name: "Test Trait Name"
                    description: "Test Trait Description"
                }) {
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
            % trait_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_trait = response.data["traitUpdate"]["trait"]

        self.assertEqual(res_trait["name"], "Test Trait Name")
        self.assertEqual(res_trait["description"], "Test Trait Description")

        updated_trait = Trait.objects.get(pk=from_global_id(res_trait["id"])[1])
        self.assertEqual(updated_trait.name, "Test Trait Name")
        self.assertEqual(updated_trait.description, "Test Trait Description")

        self.compare_traits(updated_trait, res_trait)

    def test_trait_update_bad_input_no_id(self):
        TraitFactory()
        query = """
            mutation {
                traitUpdate(input: {
                    name: "%s"
                    description: "%s"
                }) {
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_trait_update_bad_input_no_name(self):
        trait = TraitFactory()
        trait_global_id = to_global_id("TraitNode", trait.id)
        query = (
            """
            mutation {
                traitUpdate(input: {
                    id: "%s"
                    description: "Test Trait Description"
                }) {
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
            % trait_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_trait_patch(self):
        trait = TraitFactory(
            name="Not Test Trait Name", description="Test Trait Description"
        )
        trait_global_id = to_global_id("TraitNode", trait.id)
        query = (
            """
            mutation {
                traitPatch(input: {
                    id: "%s"
                    name: "Test Trait Name"
                }) {
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
            % trait_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_trait = response.data["traitPatch"]["trait"]
        self.assertEqual(res_trait["name"], "Test Trait Name")
        self.assertEqual(res_trait["description"], "Test Trait Description")

        updated_trait = Trait.objects.get(pk=trait.pk)
        self.compare_traits(updated_trait, res_trait)

    def test_trait_patch_null_name(self):
        trait = TraitFactory(
            name="Not Test Trait Name", description="Test Trait Description"
        )
        trait_global_id = to_global_id("TraitNode", trait.id)
        query = (
            """
            mutation {
                traitPatch(input: {
                    id: "%s"
                    name: null
                }) {
                    trait {
                        id
                        name
                        description
                    }
                }
            }
        """
            % trait_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_trait_delete(self):
        trait = TraitFactory()
        trait_global_id = to_global_id("TraitNode", trait.id)
        query = (
            """
            mutation {
                traitDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % trait_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        self.assertTrue(response.data["traitDelete"]["ok"])

        with self.assertRaises(Trait.DoesNotExist):
            Trait.objects.get(pk=trait.id)
