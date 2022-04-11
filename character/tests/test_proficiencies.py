from graphql_jwt.testcases import JSONWebTokenTestCase
from ..models import Proficiency
from .utils import CompareMixin
from graphql_relay import from_global_id, to_global_id
from .factories import ProficiencyFactory
from django.contrib.auth import get_user_model


class ProficiencyTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)
        self.name = "Test Proficiency Name"
        self.description = "Test Proficiency Description"
        self.proficiency_type = Proficiency.PROFICIENCY_TYPES[0][0]

    def test_proficiency_list_query(self):
        factory1 = ProficiencyFactory()
        factory2 = ProficiencyFactory()
        query = """
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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_1 = response.data["proficiencies"]["edges"][0]["node"]
        res_2 = response.data["proficiencies"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.compare_proficiencies(factory1, res_1)
        self.compare_proficiencies(factory2, res_2)
        with self.assertRaises(IndexError):
            response.data["proficiencies"]["edges"][2]

    def test_bad_proficiency_list_query(self):
        ProficiencyFactory()
        query = """
            query {
                proficiencies {
                    edges {
                        node {
                            id
                            name
                            description
                            proficiencyType
                            not_a_field
                        }
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_proficiency_detail_query(self):
        proficiency = ProficiencyFactory()
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = (
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
            % proficiency_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_proficiency = response.data["proficiency"]

        self.compare_proficiencies(proficiency, res_proficiency)

    def test_proficiency_create_mutation(self):
        query = """
            mutation {
                proficiencyCreate(input: {
                    name: "%s"
                    description: "%s"
                    proficiencyType: "%s"
                }) {
                    ok
                    errors
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """ % (
            self.name,
            self.description,
            self.proficiency_type,
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_proficiency = response.data["proficiencyCreate"]["proficiency"]

        self.assertEqual(res_proficiency["name"], self.name)
        self.assertEqual(res_proficiency["description"], self.description)
        self.assertEqual(res_proficiency["proficiencyType"], self.proficiency_type)

        created_proficiency = Proficiency.objects.get(
            pk=from_global_id(res_proficiency["id"])[1]
        )
        self.assertEqual(created_proficiency.name, self.name)
        self.assertEqual(created_proficiency.description, self.description)
        self.assertEqual(created_proficiency.proficiency_type, self.proficiency_type)

        self.compare_proficiencies(created_proficiency, res_proficiency)

    def test_proficiency_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                proficiencyCreate(input: {
                    description: "Test Proficiency Description"
                }) {
                    ok
                    errors
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_proficiency_update_mutation(self):
        proficiency = ProficiencyFactory(
            name="Not Test Proficiency Name",
            description="Not Test Proficiency Description",
        )
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = """
            mutation {
                proficiencyUpdate(input: {
                    id: "%s"
                    name: "%s"
                    description: "%s"
                    proficiencyType: "%s"
                }) {
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """ % (
            proficiency_global_id,
            self.name,
            self.description,
            self.proficiency_type,
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_proficiency = response.data["proficiencyUpdate"]["proficiency"]

        self.assertEqual(res_proficiency["name"], self.name)
        self.assertEqual(res_proficiency["description"], self.description)

        updated_proficiency = Proficiency.objects.get(
            pk=from_global_id(res_proficiency["id"])[1]
        )
        self.assertEqual(updated_proficiency.name, self.name)
        self.assertEqual(updated_proficiency.description, self.description)

        self.compare_proficiencies(updated_proficiency, res_proficiency)

    def test_proficiency_update_bad_input_no_id(self):
        ProficiencyFactory()
        query = """
            mutation {
                proficiencyUpdate(input: {
                    name: "Test Proficiency Name"
                    description: "Test Proficiency Description"
                }) {
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_proficiency_update_bad_input_no_name(self):
        proficiency = ProficiencyFactory()
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = (
            """
            mutation {
                proficiencyUpdate(input: {
                    id: "%s"
                    description: "Test Proficiency Description"
                }) {
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """
            % proficiency_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_proficiency_patch(self):
        proficiency = ProficiencyFactory(
            name="Test Proficiency Name", description="Not Test Proficiency Description"
        )
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = (
            """
            mutation {
                proficiencyPatch(input: {
                    id: "%s"
                    description: "Test Proficiency Description"
                }) {
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """
            % proficiency_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_proficiency = response.data["proficiencyPatch"]["proficiency"]
        self.assertEqual(res_proficiency["name"], "Test Proficiency Name")
        self.assertEqual(res_proficiency["description"], "Test Proficiency Description")

    def test_proficiency_patch_null_name(self):
        proficiency = ProficiencyFactory(
            name="Not Test Proficiency Name", description="Test Proficiency Description"
        )
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = (
            """
            mutation {
                proficiencyPatch(input: {
                    id: "%s"
                    name: null
                }) {
                    proficiency {
                        id
                        name
                        description
                        proficiencyType
                    }
                }
            }
        """
            % proficiency_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_proficiency_delete(self):
        proficiency = ProficiencyFactory()
        proficiency_global_id = to_global_id("ProficiencyNode", proficiency.id)
        query = (
            """
            mutation {
                proficiencyDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % proficiency_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        self.assertTrue(response.data["proficiencyDelete"]["ok"])

        with self.assertRaises(Proficiency.DoesNotExist):
            Proficiency.objects.get(pk=proficiency.id)
