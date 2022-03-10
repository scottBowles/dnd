import json
import factory
from graphene_django.utils.testing import GraphQLTestCase
from ..models import Script
from graphql_relay import from_global_id, to_global_id


class ScriptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Script

    name = factory.Faker("name")


class ScriptTests(GraphQLTestCase):
    def test_script_list_query(self):
        factory1 = ScriptFactory()
        factory2 = ScriptFactory()
        query = """
            query {
                scripts {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_1 = result["data"]["scripts"]["edges"][0]["node"]
        res_2 = result["data"]["scripts"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.assertEqual(from_global_id(res_1["id"])[1], str(factory1.id))
        self.assertEqual(res_1["name"], factory1.name)
        self.assertEqual(from_global_id(res_2["id"])[1], str(factory2.id))
        self.assertEqual(res_2["name"], factory2.name)
        with self.assertRaises(IndexError):
            result["data"]["scripts"]["edges"][2]

    def test_bad_script_list_query(self):
        ScriptFactory()
        query = """
            query {
                scripts {
                    edges {
                        node {
                            id
                            name
                            not_a_field
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_script_detail_query(self):
        script = ScriptFactory()
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            query {
                script(id: "%s") {
                    id
                    name
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_script = result["data"]["script"]

        self.assertEqual(res_script["name"], script.name)

    def test_script_create_mutation(self):
        query = """
            mutation {
                scriptCreate(input: {
                    name: "Test Script Name"
                }) {
                    ok
                    errors
                    script {
                        id
                        name
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_script = result["data"]["scriptCreate"]["script"]

        self.assertEqual(res_script["name"], "Test Script Name")

        created_script = Script.objects.get(pk=from_global_id(res_script["id"])[1])
        self.assertEqual(created_script.name, "Test Script Name")

    def test_script_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                scriptCreate(input: {
                    description: "Test Script Description"
                }) {
                    ok
                    errors
                    script {
                        id
                        name
                        created
                        updated
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_script_update_mutation(self):
        script = ScriptFactory(name="Not Test Script Name")
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            mutation {
                scriptUpdate(input: {
                    id: "%s"
                    name: "Test Script Name"
                }) {
                    script {
                        id
                        name
                    }
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_script = result["data"]["scriptUpdate"]["script"]

        self.assertEqual(res_script["name"], "Test Script Name")

        updated_script = Script.objects.get(pk=from_global_id(res_script["id"])[1])
        self.assertEqual(updated_script.name, "Test Script Name")

    def test_script_update_bad_input_no_id(self):
        ScriptFactory()
        query = """
            mutation {
                scriptUpdate(input: {
                    name: "Test Script Name"
                }) {
                    script {
                        id
                        name
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_script_update_bad_input_no_name(self):
        script = ScriptFactory()
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            mutation {
                scriptUpdate(input: {
                    id: "%s"
                }) {
                    script {
                        id
                        name
                    }
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_script_patch(self):
        script = ScriptFactory(name="Not Test Script Name")
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            mutation {
                scriptPatch(input: {
                    id: "%s"
                    name: "Test Script Name"
                }) {
                    script {
                        id
                        name
                    }
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_script = result["data"]["scriptPatch"]["script"]
        self.assertEqual(res_script["name"], "Test Script Name")

    def test_script_patch_null_name(self):
        script = ScriptFactory(name="Not Test Script Name")
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            mutation {
                scriptPatch(input: {
                    id: "%s"
                    name: null
                }) {
                    script {
                        id
                        name
                    }
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_script_delete(self):
        script = ScriptFactory()
        script_global_id = to_global_id("ScriptNode", script.id)
        query = (
            """
            mutation {
                scriptDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % script_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["scriptDelete"]["ok"])

        with self.assertRaises(Script.DoesNotExist):
            Script.objects.get(pk=script.id)
