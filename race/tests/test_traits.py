import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import from_global_id, to_global_id
from .factories import TraitFactory
from .utils import CompareMixin
from ..models import Trait


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


class TraitMutationTests(CompareMixin, GraphQLTestCase):
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

        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_trait = result["data"]["traitCreate"]["trait"]

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
        response = self.query(query)
        self.assertResponseHasErrors(response)

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
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_trait = result["data"]["traitUpdate"]["trait"]

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
        response = self.query(query)
        self.assertResponseHasErrors(response)

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
        response = self.query(query)
        self.assertResponseHasErrors(response)

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
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_trait = result["data"]["traitPatch"]["trait"]
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
        response = self.query(query)
        self.assertResponseHasErrors(response)

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
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["traitDelete"]["ok"])

        with self.assertRaises(Trait.DoesNotExist):
            Trait.objects.get(pk=trait.id)
