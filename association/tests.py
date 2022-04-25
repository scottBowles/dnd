import factory
from .models import Association
from graphql_relay import from_global_id, to_global_id
from django.contrib.auth import get_user_model

from graphql_jwt.testcases import JSONWebTokenTestCase


class AssociationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Association

    name = factory.Faker("name")
    description = factory.Faker("text")
    image_ids = factory.List([factory.Faker("text") for _ in range(3)])
    thumbnail_id = factory.Faker("text")


class AssociationTests(JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

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
                            imageIds
                            thumbnailId
                        }
                    }
                }
            }
        """
        response = self.client.execute(query)
        result = response.data

        res_1 = result["associations"]["edges"][0]["node"]
        res_2 = result["associations"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.assertEqual(from_global_id(res_1["id"])[1], str(factory1.id))
        self.assertEqual(res_1["name"], factory1.name)
        self.assertEqual(res_1["description"], factory1.description)
        self.assertEqual(res_1["imageIds"], factory1.image_ids)
        self.assertEqual(res_1["thumbnailId"], factory1.thumbnail_id)
        self.assertEqual(from_global_id(res_2["id"])[1], str(factory2.id))
        self.assertEqual(res_2["name"], factory2.name)
        self.assertEqual(res_2["description"], factory2.description)
        self.assertEqual(res_2["imageIds"], factory2.image_ids)
        self.assertEqual(res_2["thumbnailId"], factory2.thumbnail_id)
        with self.assertRaises(IndexError):
            result["associations"]["edges"][2]

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
        response = self.client.execute(query)

        self.assertIsNotNone(response.errors)
        self.assertIsNone(response.data)

    def test_association_detail_query(self):
        association = AssociationFactory()
        association_global_id = to_global_id("AssociationNode", association.id)
        query = """
            query GetAssociation($id: ID!) {
                association(id: $id) {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                }
            }
        """
        variables = {"id": association_global_id}
        response = self.client.execute(query, variables)
        self.assertIsNone(response.errors)

        res_association = response.data["association"]

        self.assertEqual(res_association["name"], association.name)
        self.assertEqual(res_association["description"], association.description)
        self.assertEqual(res_association["imageIds"], association.image_ids)
        self.assertEqual(res_association["thumbnailId"], association.thumbnail_id)

    def test_association_create_mutation(self):
        query = """
            mutation {
                associationCreate(input: {
                    name: "Test Assoc Name"
                    description: "Test Assoc Description"
                    imageIds: ["Test Assoc Image ID 1", "Test Assoc Image ID 2", "Test Assoc Image ID 3"]
                    thumbnailId: "Test Assoc Thumbnail ID"
                }) {
                    ok
                    errors
                    association {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_association = response.data["associationCreate"]["association"]

        self.assertEqual(res_association["name"], "Test Assoc Name")
        self.assertEqual(res_association["description"], "Test Assoc Description")
        self.assertEqual(
            res_association["imageIds"],
            ["Test Assoc Image ID 1", "Test Assoc Image ID 2", "Test Assoc Image ID 3"],
        )
        self.assertEqual(res_association["thumbnailId"], "Test Assoc Thumbnail ID")

        created_association = Association.objects.get(
            pk=from_global_id(res_association["id"])[1]
        )
        self.assertEqual(created_association.name, "Test Assoc Name")
        self.assertEqual(created_association.description, "Test Assoc Description")
        self.assertEqual(
            created_association.image_ids,
            ["Test Assoc Image ID 1", "Test Assoc Image ID 2", "Test Assoc Image ID 3"],
        )
        self.assertEqual(created_association.thumbnail_id, "Test Assoc Thumbnail ID")

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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_association_update_mutation(self):
        association = AssociationFactory(
            name="Not Test Assoc Name", description="Not Test Assoc Description"
        )
        association_global_id = to_global_id("AssociationNode", association.id)
        query = """
            mutation UpdateAssociation($input: AssociationUpdateMutationInput!) {
                associationUpdate(input: $input) {
                    association {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                    }
                }
            }
        """
        variables = {
            "input": {
                "id": association_global_id,
                "name": "Test Assoc Name",
                "description": "Test Assoc Description",
                "imageIds": [
                    "Test Assoc Image ID 1",
                    "Test Assoc Image ID 2",
                    "Test Assoc Image ID 3",
                ],
                "thumbnailId": "Test Assoc Thumbnail ID",
            }
        }
        response = self.client.execute(query, variables)
        self.assertIsNone(response.errors)

        res_association = response.data["associationUpdate"]["association"]

        self.assertEqual(res_association["name"], "Test Assoc Name")
        self.assertEqual(res_association["description"], "Test Assoc Description")
        self.assertEqual(
            res_association["imageIds"],
            ["Test Assoc Image ID 1", "Test Assoc Image ID 2", "Test Assoc Image ID 3"],
        )
        self.assertEqual(res_association["thumbnailId"], "Test Assoc Thumbnail ID")

        updated_association = Association.objects.get(
            pk=from_global_id(res_association["id"])[1]
        )
        self.assertEqual(updated_association.name, "Test Assoc Name")
        self.assertEqual(updated_association.description, "Test Assoc Description")
        self.assertEqual(
            updated_association.image_ids,
            ["Test Assoc Image ID 1", "Test Assoc Image ID 2", "Test Assoc Image ID 3"],
        )
        self.assertEqual(updated_association.thumbnail_id, "Test Assoc Thumbnail ID")

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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_association = response.data["associationPatch"]["association"]
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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        self.assertTrue(response.data["associationDelete"]["ok"])

        with self.assertRaises(Association.DoesNotExist):
            Association.objects.get(pk=association.id)
