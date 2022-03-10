import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import SkillFactory
from .utils import CompareMixin


class SkillTests(CompareMixin, GraphQLTestCase):
    def test_skill_detail_query(self):
        skill = SkillFactory()
        response = self.query(
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
            % to_global_id("SkillNode", skill.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_skill = res_json["data"]["skill"]
        self.compare_skills(skill, res_skill)

    def test_skill_list_query(self):
        num_skills = random.randint(0, 10)
        skills = SkillFactory.create_batch(num_skills)
        response = self.query(
            """
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
        )
        self.assertResponseNoErrors(response)
        res_json = json.loads(response.content)
        res_skills = res_json["data"]["skills"]["edges"]
        self.assertEqual(len(res_skills), num_skills)
        for i, skill in enumerate(skills):
            res_skill = res_skills[i]["node"]
            self.compare_skills(skill, res_skill)
