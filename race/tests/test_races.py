import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import from_global_id, to_global_id
from .factories import RaceFactory, AbilityScoreIncreaseFactory, TraitFactory
from character.tests.factories import LanguageFactory


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


class RaceQueryTests(CompareMixin, GraphQLTestCase):
    def test_basic_race_detail_query(self):
        race = RaceFactory()

        response = self.query(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    ageOfAdulthood
                    lifeExpectancy
                    alignment
                    size
                    speed
                }
            }
            """
            % to_global_id("RaceNode", race.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_race = res_json["data"]["race"]

        self.compare_races(race, res_race)

    def test_race_detail_query_with_relations(self):
        ability_score_increases = AbilityScoreIncreaseFactory.create_batch(
            random.randint(0, 3)
        )
        languages = LanguageFactory.create_batch(random.randint(0, 3))
        traits = TraitFactory.create_batch(random.randint(0, 3))
        race = RaceFactory(
            languages=languages,
            traits=traits,
            ability_score_increases=ability_score_increases,
        )

        response = self.query(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    ageOfAdulthood
                    lifeExpectancy
                    alignment
                    size
                    speed
                    abilityScoreIncreases {
                        edges {
                            node {
                                abilityScore
                                increase
                            }
                        }
                    }
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
            }
            """
            % to_global_id("RaceNode", race.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_race = res_json["data"]["race"]

        self.compare_races(
            race,
            res_race,
            compare_ability_score_increases=True,
            compare_languages=True,
            compare_traits=True,
        )

    def test_race_detail_query_with_base_and_sub_races(self):
        base_race = RaceFactory()
        race = RaceFactory()
        subraces = RaceFactory.create_batch(2)
        for r in subraces:
            race.subraces.add(r)
        race = RaceFactory(base_race=base_race)

        response = self.query(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    ageOfAdulthood
                    lifeExpectancy
                    alignment
                    size
                    speed
                    baseRace {
                        id
                        name
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
                    }
                    subraces {
                        edges {
                            node {
                                id
                                name
                                ageOfAdulthood
                                lifeExpectancy
                                alignment
                                size
                                speed
                            }
                        }
                    }
                }
            }
            """
            % to_global_id("RaceNode", race.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_race = res_json["data"]["race"]

        self.compare_races(
            race, res_race, compare_base_races_to_depth=1, compare_subraces=True
        )

    def test_basic_race_list_query(self):
        races = RaceFactory.create_batch(random.randint(0, 3))

        response = self.query(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            ageOfAdulthood
                            lifeExpectancy
                            alignment
                            size
                            speed
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_races = res_json["data"]["races"]["edges"]

        for i, race in enumerate(races):
            self.compare_races(race, res_races[i]["node"])

    def test_race_list_query_with_relations(self):
        races = []
        for i in range(random.randint(0, 3)):
            languages = LanguageFactory.create_batch(random.randint(0, 3))
            traits = TraitFactory.create_batch(random.randint(0, 3))
            race = RaceFactory(languages=languages, traits=traits)
            races.append(race)

        response = self.query(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            ageOfAdulthood
                            lifeExpectancy
                            alignment
                            size
                            speed
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
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_races = res_json["data"]["races"]["edges"]

        for i, race in enumerate(races):
            self.compare_races(
                race, res_races[i]["node"], compare_languages=True, compare_traits=True
            )

    def test_race_list_query_with_base_and_sub_races(self):
        base_races = RaceFactory.create_batch(2)
        races = [
            RaceFactory(),
            RaceFactory(base_race=base_races[0]),
            RaceFactory(base_race=base_races[1]),
        ]
        all_subraces = []
        for race in races:
            subraces = RaceFactory.create_batch(random.randint(0, 3))
            for subrace in subraces:
                race.subraces.add(subrace)
                all_subraces.append(subrace)
        all_races = [*base_races, *races, *all_subraces]

        response = self.query(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            ageOfAdulthood
                            lifeExpectancy
                            alignment
                            size
                            speed
                            baseRace {
                                id
                                name
                                ageOfAdulthood
                                lifeExpectancy
                                alignment
                                size
                                speed
                            }
                            subraces {
                                edges {
                                    node {
                                        id
                                        name
                                        ageOfAdulthood
                                        lifeExpectancy
                                        alignment
                                        size
                                        speed
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_races = res_json["data"]["races"]["edges"]

        for i, race in enumerate(all_races):
            self.compare_races(
                race,
                res_races[i]["node"],
                compare_base_races_to_depth=1,
                compare_subraces=True,
            )

