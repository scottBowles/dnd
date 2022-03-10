import json
import factory
from graphene_django.utils.testing import GraphQLTestCase
from .models import Association
from graphql_relay import from_global_id, to_global_id


class AssociationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Association

    name = factory.Faker("name")
    description = factory.Faker("text")


class AssociationTests(GraphQLTestCase):
    def test_association_list_query(self):
        factory1 = AssociationFactory()
        factory2 = AssociationFactory()
        query = """
            query {
                associations {
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
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_1 = result["data"]["associations"]["edges"][0]["node"]
        res_2 = result["data"]["associations"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.assertEqual(from_global_id(res_1["id"])[1], str(factory1.id))
        self.assertEqual(res_1["name"], factory1.name)
        self.assertEqual(res_1["description"], factory1.description)
        self.assertEqual(from_global_id(res_2["id"])[1], str(factory2.id))
        self.assertEqual(res_2["name"], factory2.name)
        self.assertEqual(res_2["description"], factory2.description)
        with self.assertRaises(IndexError):
            result["data"]["associations"]["edges"][2]

    def test_bad_association_list_query(self):
        AssociationFactory()
        query = """
            query {
                associations {
                    edges {
                        node {
                            id
                            name
                            description
                            not_a_field
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_association_detail_query(self):
        association = AssociationFactory()
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            query {
                association(id: "%s") {
                    id
                    name
                    description
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_association = result["data"]["association"]

        self.assertEqual(res_association["name"], association.name)
        self.assertEqual(res_association["description"], association.description)

    def test_association_create_mutation(self):
        query = """
            mutation {
                associationCreate(input: {
                    name: "Test Assoc Name"
                    description: "Test Assoc Description"
                }) {
                    ok
                    errors
                    association {
                        id
                        name
                        description
                        created
                        updated
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_association = result["data"]["associationCreate"]["association"]

        self.assertEqual(res_association["name"], "Test Assoc Name")
        self.assertEqual(res_association["description"], "Test Assoc Description")

        created_association = Association.objects.get(
            pk=from_global_id(res_association["id"])[1]
        )
        self.assertEqual(created_association.name, "Test Assoc Name")
        self.assertEqual(created_association.description, "Test Assoc Description")

    def test_association_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                associationCreate(input: {
                    description: "Test Assoc Description"
                }) {
                    ok
                    errors
                    association {
                        id
                        name
                        description
                        created
                        updated
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_association_update_mutation(self):
        association = AssociationFactory(
            name="Not Test Assoc Name", description="Not Test Assoc Description"
        )
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            mutation {
                associationUpdate(input: {
                    id: "%s"
                    name: "Test Assoc Name"
                    description: "Test Assoc Description"
                }) {
                    association {
                        id
                        name
                        description
                    }
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_association = result["data"]["associationUpdate"]["association"]

        self.assertEqual(res_association["name"], "Test Assoc Name")
        self.assertEqual(res_association["description"], "Test Assoc Description")

        updated_association = Association.objects.get(
            pk=from_global_id(res_association["id"])[1]
        )
        self.assertEqual(updated_association.name, "Test Assoc Name")
        self.assertEqual(updated_association.description, "Test Assoc Description")

    def test_association_update_bad_input_no_id(self):
        AssociationFactory()
        query = """
            mutation {
                associationUpdate(input: {
                    name: "Test Assoc Name"
                    description: "Test Assoc Description"
                }) {
                    association {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_association_update_bad_input_no_name(self):
        association = AssociationFactory()
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            mutation {
                associationUpdate(input: {
                    id: "%s"
                    description: "Test Assoc Description"
                }) {
                    association {
                        id
                        name
                        description
                    }
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_association_patch(self):
        association = AssociationFactory(
            name="Not Test Assoc Name", description="Test Assoc Description"
        )
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            mutation {
                associationPatch(input: {
                    id: "%s"
                    name: "Test Assoc Name"
                }) {
                    association {
                        id
                        name
                        description
                    }
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_association = result["data"]["associationPatch"]["association"]
        self.assertEqual(res_association["name"], "Test Assoc Name")
        self.assertEqual(res_association["description"], "Test Assoc Description")

    def test_association_patch_null_name(self):
        association = AssociationFactory(
            name="Not Test Assoc Name", description="Test Assoc Description"
        )
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            mutation {
                associationPatch(input: {
                    id: "%s"
                    name: null
                }) {
                    association {
                        id
                        name
                        description
                    }
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_association_delete(self):
        association = AssociationFactory()
        association_global_id = to_global_id("AssociationNode", association.id)
        query = (
            """
            mutation {
                associationDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % association_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["associationDelete"]["ok"])

        with self.assertRaises(Association.DoesNotExist):
            Association.objects.get(pk=association.id)
