import json
from graphene_django.utils.testing import GraphQLTestCase
from ..models import Skill, ABILITIES
from .utils import CompareMixin
from graphql_relay import from_global_id, to_global_id
from .factories import SkillFactory


class SkillTests(CompareMixin, GraphQLTestCase):
    def setUp(self):
        self.name = "Test Skill Name"
        self.description = "Test Skill Description"
        self.related_ability = ABILITIES[0][0]

    def test_skill_list_query(self):
        factory1 = SkillFactory()
        factory2 = SkillFactory()
        query = """
            query {
                skills {
                    edges {
                        node {
                            id
                            name
                            description
                            relatedAbility
                            custom
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_1 = result["data"]["skills"]["edges"][0]["node"]
        res_2 = result["data"]["skills"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.compare_skills(factory1, res_1)
        self.compare_skills(factory2, res_2)
        with self.assertRaises(IndexError):
            result["data"]["skills"]["edges"][2]

    def test_bad_skill_list_query(self):
        SkillFactory()
        query = """
            query {
                skills {
                    edges {
                        node {
                            id
                            name
                            description
                            relatedAbility
                            custom
                            not_a_field
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_skill_detail_query(self):
        skill = SkillFactory()
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = (
            """
            query {
                skill(id: "%s") {
                    id
                    name
                    description
                    relatedAbility
                    custom
                }
            }
        """
            % skill_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_skill = result["data"]["skill"]

        self.compare_skills(skill, res_skill)

    def test_skill_create_mutation(self):
        query = """
            mutation {
                skillCreate(input: {
                    name: "%s"
                    description: "%s"
                    relatedAbility: "%s"
                    custom: false
                }) {
                    ok
                    errors
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """ % (
            self.name,
            self.description,
            self.related_ability,
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_skill = result["data"]["skillCreate"]["skill"]

        self.assertEqual(res_skill["name"], self.name)
        self.assertEqual(res_skill["description"], self.description)
        self.assertEqual(res_skill["relatedAbility"], self.related_ability)
        self.assertEqual(res_skill["custom"], False)

        created_skill = Skill.objects.get(pk=from_global_id(res_skill["id"])[1])
        self.assertEqual(created_skill.name, self.name)
        self.assertEqual(created_skill.description, self.description)
        self.assertEqual(created_skill.related_ability, self.related_ability)
        self.assertEqual(created_skill.custom, False)

        self.compare_skills(created_skill, res_skill)

    def test_skill_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                skillCreate(input: {
                    description: "Test Skill Description"
                }) {
                    ok
                    errors
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_skill_update_mutation(self):
        skill = SkillFactory(
            name="Not Test Skill Name", description="Not Test Skill Description"
        )
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = """
            mutation {
                skillUpdate(input: {
                    id: "%s"
                    name: "%s"
                    description: "%s"
                    relatedAbility: "%s"
                    custom: true
                }) {
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """ % (
            skill_global_id,
            self.name,
            self.description,
            self.related_ability,
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_skill = result["data"]["skillUpdate"]["skill"]

        self.assertEqual(res_skill["name"], self.name)
        self.assertEqual(res_skill["description"], self.description)

        updated_skill = Skill.objects.get(pk=from_global_id(res_skill["id"])[1])
        self.assertEqual(updated_skill.name, self.name)
        self.assertEqual(updated_skill.description, self.description)

        self.compare_skills(updated_skill, res_skill)

    def test_skill_update_bad_input_no_id(self):
        SkillFactory()
        query = """
            mutation {
                skillUpdate(input: {
                    name: "Test Skill Name"
                    description: "Test Skill Description"
                }) {
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_skill_update_bad_input_no_name(self):
        skill = SkillFactory()
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = (
            """
            mutation {
                skillUpdate(input: {
                    id: "%s"
                    description: "Test Skill Description"
                }) {
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """
            % skill_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_skill_patch(self):
        skill = SkillFactory(
            name="Test Skill Name", description="Not Test Skill Description"
        )
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = (
            """
            mutation {
                skillPatch(input: {
                    id: "%s"
                    description: "Test Skill Description"
                }) {
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """
            % skill_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_skill = result["data"]["skillPatch"]["skill"]
        self.assertEqual(res_skill["name"], "Test Skill Name")
        self.assertEqual(res_skill["description"], "Test Skill Description")

    def test_skill_patch_null_name(self):
        skill = SkillFactory(
            name="Not Test Skill Name", description="Test Skill Description"
        )
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = (
            """
            mutation {
                skillPatch(input: {
                    id: "%s"
                    name: null
                }) {
                    skill {
                        id
                        name
                        description
                        relatedAbility
                        custom
                    }
                }
            }
        """
            % skill_global_id
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_skill_delete(self):
        skill = SkillFactory()
        skill_global_id = to_global_id("SkillNode", skill.id)
        query = (
            """
            mutation {
                skillDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % skill_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["skillDelete"]["ok"])

        with self.assertRaises(Skill.DoesNotExist):
            Skill.objects.get(pk=skill.id)
