import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import from_global_id, to_global_id
from .factories import LanguageFactory, ScriptFactory
from .utils import CompareMixin
from ..models import Language


class LanguageTests(CompareMixin, GraphQLTestCase):
    def test_language_detail_query(self):
        language = LanguageFactory()
        response = self.query(
            """
            query {
                language(id: "%s") {
                    id
                    name
                    description
                    script {
                        name
                    }
                }
            }
            """
            % to_global_id("LanguageNode", language.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_language = res_json["data"]["language"]
        self.compare_languages(language, res_language)

    def test_language_list_query(self):
        num_languages = random.randint(0, 10)
        languages = LanguageFactory.create_batch(num_languages)
        response = self.query(
            """
            query {
                languages {
                    edges {
                        node {
                            id
                            name
                            description
                            script {
                                name
                            }
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)
        res_json = json.loads(response.content)
        res_languages = res_json["data"]["languages"]["edges"]
        self.assertEqual(len(res_languages), num_languages)
        for i, language in enumerate(languages):
            res_language = res_languages[i]["node"]
            self.compare_languages(language, res_language)

    def test_language_create_mutation_without_script(self):
        name = "Test Language Name"
        description = "Test Language Description"
        query = """
            mutation {
                languageCreate(input: {
                    name: "%s",
                    description: "%s",
                }) {
                    ok
                    errors
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
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
        res_language = result["data"]["languageCreate"]["language"]

        self.assertEqual(res_language["name"], name)
        self.assertEqual(res_language["description"], description)

        created_language = Language.objects.get(
            pk=from_global_id(res_language["id"])[1]
        )
        self.assertEqual(created_language.name, name)
        self.assertEqual(created_language.description, description)

        self.compare_languages(created_language, res_language)

    def test_language_create_mutation_with_script(self):
        name = "Test Language Name"
        description = "Test Language Description"
        script = ScriptFactory()

        query = """
            mutation {
                languageCreate(input: {
                    name: "%s",
                    description: "%s",
                    script: "%s",
                }) {
                    ok
                    errors
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
                    }
                }
            }
        """ % (
            name,
            description,
            to_global_id("ScriptNode", script.id),
        )

        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_language = result["data"]["languageCreate"]["language"]

        self.assertEqual(res_language["name"], name)
        self.assertEqual(res_language["description"], description)
        self.assertEqual(res_language["script"]["name"], script.name)

        created_language = Language.objects.get(
            pk=from_global_id(res_language["id"])[1]
        )
        self.assertEqual(created_language.name, name)
        self.assertEqual(created_language.description, description)
        self.assertEqual(created_language.script.name, script.name)

        self.compare_languages(created_language, res_language)

    def test_language_create_bad_input(self):
        query = """
            mutation {
                languageCreate(input: {
                    description: "Test language Description"
                }) {
                    ok
                    errors
                    language {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_language_update_mutation_without_script(self):
        language = LanguageFactory(
            name="Not Test Language Name", description="Not Test Language Description"
        )
        language_global_id = to_global_id("LanguageNode", language.id)
        query = (
            """
            mutation {
                languageUpdate(input: {
                    id: "%s"
                    name: "Test Language Name"
                    description: "Test Language Description"
                }) {
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
                    }
                }
            }
        """
            % language_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_language = result["data"]["languageUpdate"]["language"]

        self.assertEqual(res_language["name"], "Test Language Name")
        self.assertEqual(res_language["description"], "Test Language Description")

        updated_language = Language.objects.get(
            pk=from_global_id(res_language["id"])[1]
        )
        self.assertEqual(updated_language.name, "Test Language Name")
        self.assertEqual(updated_language.description, "Test Language Description")

        self.compare_languages(updated_language, res_language)

    def test_language_update_mutation_with_script(self):
        language = LanguageFactory(
            name="Not Test Language Name", description="Not Test Language Description"
        )
        language_global_id = to_global_id("LanguageNode", language.id)
        new_script = ScriptFactory()
        script_global_id = to_global_id("ScriptNode", new_script.id)
        query = """
            mutation {
                languageUpdate(input: {
                    id: "%s"
                    name: "Test Language Name"
                    description: "Test Language Description"
                    script: "%s"
                }) {
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
                    }
                }
            }
        """ % (
            language_global_id,
            script_global_id,
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_language = result["data"]["languageUpdate"]["language"]

        self.assertEqual(res_language["name"], "Test Language Name")
        self.assertEqual(res_language["description"], "Test Language Description")
        self.assertEqual(res_language["script"]["name"], new_script.name)

        updated_language = Language.objects.get(
            pk=from_global_id(res_language["id"])[1]
        )
        self.assertEqual(updated_language.name, "Test Language Name")
        self.assertEqual(updated_language.description, "Test Language Description")
        self.assertEqual(updated_language.script.name, new_script.name)

        self.compare_languages(updated_language, res_language)

    def test_language_update_bad_input_no_id(self):
        LanguageFactory()
        query = """
            mutation {
                languageUpdate(input: {
                    name: "%s"
                    description: "%s"
                }) {
                    language {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_language_update_bad_input_no_name(self):
        language = LanguageFactory()
        language_global_id = to_global_id("LanguageNode", language.id)
        query = (
            """
            mutation {
                languageUpdate(input: {
                    id: "%s"
                    description: "Test Language Description"
                }) {
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
                    }
                }
            }
        """
            % language_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_language_patch(self):
        language = LanguageFactory(
            name="Not Test Language Name", description="Test Language Description"
        )
        language_global_id = to_global_id("LanguageNode", language.id)
        query = (
            """
            mutation {
                languagePatch(input: {
                    id: "%s"
                    name: "Test Language Name"
                }) {
                    language {
                        id
                        name
                        description
                        script {
                            name
                        }
                    }
                }
            }
        """
            % language_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_language = result["data"]["languagePatch"]["language"]
        self.assertEqual(res_language["name"], "Test Language Name")
        self.assertEqual(res_language["description"], "Test Language Description")

        updated_language = Language.objects.get(pk=language.pk)
        self.compare_languages(updated_language, res_language)

    def test_language_patch_null_name(self):
        language = LanguageFactory(
            name="Not Test Language Name", description="Test Language Description"
        )
        language_global_id = to_global_id("LanguageNode", language.id)
        query = (
            """
            mutation {
                languagePatch(input: {
                    id: "%s"
                    name: null
                }) {
                    language {
                        id
                        name
                        description
                    }
                }
            }
        """
            % language_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_language_delete(self):
        language = LanguageFactory()
        language_global_id = to_global_id("LanguageNode", language.id)
        query = (
            """
            mutation {
                languageDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % language_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["languageDelete"]["ok"])

        with self.assertRaises(Language.DoesNotExist):
            Language.objects.get(pk=language.id)
