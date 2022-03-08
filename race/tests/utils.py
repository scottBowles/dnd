from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import from_global_id


class CompareMixin(GraphQLTestCase):
    def compare_races(
        self,
        model_race,
        node_race,
        compare_base_races_to_depth=0,
        compare_subraces=False,
        compare_ability_score_increases=False,
        compare_languages=False,
        compare_traits=False,
    ):
        if model_race is None:
            self.assertIsNone(node_race)
            return

        self.assertEqual(str(model_race.id), from_global_id(node_race["id"])[1])
        self.assertEqual(model_race.name, node_race["name"])
        self.assertEqual(model_race.age_of_adulthood, node_race["ageOfAdulthood"])
        self.assertEqual(model_race.life_expectancy, node_race["lifeExpectancy"])
        self.assertEqual(model_race.alignment, node_race["alignment"])
        self.assertEqual(model_race.size, node_race["size"])
        self.assertEqual(model_race.speed, node_race["speed"])
        if compare_base_races_to_depth > 0:
            self.compare_races(
                model_race.base_race,
                node_race.get("baseRace", None),
                compare_base_races_to_depth=compare_base_races_to_depth - 1,
            )

        if compare_subraces:
            model_subraces = model_race.subraces.all()
            node_subraces = node_race["subraces"]["edges"]
            for i, model_subrace in enumerate(model_subraces):
                self.compare_races(model_subrace, node_subraces[i]["node"])

        if compare_languages:
            model_languages = model_race.languages.all()
            node_languages = node_race["languages"]["edges"]
            for i, model_language in enumerate(model_languages):
                self.compare_languages(model_language, node_languages[i]["node"])

        if compare_traits:
            model_traits = model_race.traits.all()
            node_traits = node_race["traits"]["edges"]
            for i, model_trait in enumerate(model_traits):
                self.compare_traits(model_trait, node_traits[i]["node"])

        if compare_ability_score_increases:
            model_ability_score_increases = model_race.ability_score_increases.all()
            node_ability_score_increases = node_race["abilityScoreIncreases"]["edges"]
            for i, model_asi in enumerate(model_ability_score_increases):
                self.compare_ability_score_increases(
                    model_asi, node_ability_score_increases[i]["node"]
                )

    def compare_ability_score_increases(self, model_asi, node_asi):
        self.assertEqual(model_asi.ability_score, node_asi["abilityScore"])
        self.assertEqual(model_asi.increase, node_asi["increase"])

    def compare_languages(self, model_language, node_language):
        self.assertEqual(str(model_language.id), from_global_id(node_language["id"])[1])
        self.assertEqual(model_language.name, node_language["name"])
        self.assertEqual(model_language.description, node_language["description"])
        self.assertEqual(model_language.script.name, node_language["script"]["name"])

    def compare_traits(self, model_trait, node_trait):
        self.assertEqual(str(model_trait.id), from_global_id(node_trait["id"])[1])
        self.assertEqual(model_trait.name, node_trait["name"])
        self.assertEqual(model_trait.description, node_trait["description"])
