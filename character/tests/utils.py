from graphql_jwt.testcases import JSONWebTokenTestCase
from graphql_relay import from_global_id
from race.tests import test_races


class CompareMixin(test_races.CompareMixin, JSONWebTokenTestCase):
    def compare_npcs(
        self, model_npc, node_npc, compare_features=False, compare_proficiencies=False
    ):
        self.assertEqual(str(model_npc.id), from_global_id(node_npc["id"])[1])
        self.assertEqual(model_npc.name, node_npc["name"])
        self.assertEqual(model_npc.description, node_npc["description"])
        self.assertEqual(model_npc.image_ids, node_npc["imageIds"])
        self.assertEqual(model_npc.thumbnail_id, node_npc["thumbnailId"])
        self.assertEqual(model_npc.size, node_npc["size"])
        self.compare_races(model_npc.race, node_npc["race"])
        if compare_features:
            for i, feature in enumerate(model_npc.features_and_traits.all()):
                self.compare_features(
                    feature, node_npc["featuresAndTraits"]["edges"][i]["node"]
                )
        if compare_proficiencies:
            for i, proficiency in enumerate(model_npc.proficiencies.all()):
                self.compare_proficiencies(
                    proficiency, node_npc["proficiencies"]["edges"][i]["node"]
                )

    def compare_features(self, model_feature, node_feature):
        self.assertEqual(str(model_feature.id), from_global_id(node_feature["id"])[1])
        self.assertEqual(model_feature.name, node_feature["name"])
        self.assertEqual(model_feature.description, node_feature["description"])

    def compare_proficiencies(self, model_proficiency, node_proficiency):
        self.assertEqual(
            str(model_proficiency.id), from_global_id(node_proficiency["id"])[1]
        )
        self.assertEqual(model_proficiency.name, node_proficiency["name"])
        self.assertEqual(model_proficiency.description, node_proficiency["description"])
        self.assertEqual(
            model_proficiency.proficiency_type, node_proficiency["proficiencyType"]
        )

    def compare_skills(self, model_skill, node_skill):
        self.assertEqual(str(model_skill.id), from_global_id(node_skill["id"])[1])
        self.assertEqual(model_skill.name, node_skill["name"])
        self.assertEqual(model_skill.description, node_skill["description"])
        self.assertEqual(model_skill.related_ability, node_skill["relatedAbility"])
        self.assertEqual(model_skill.custom, node_skill["custom"])

    def compare_languages(self, model_language, node_language):
        self.assertEqual(str(model_language.id), from_global_id(node_language["id"])[1])
        self.assertEqual(model_language.name, node_language["name"])
        self.assertEqual(model_language.description, node_language["description"])
        if model_language.script:
            self.assertEqual(
                model_language.script.name, node_language["script"]["name"]
            )
        else:
            self.assertEqual(node_language["script"], None)
