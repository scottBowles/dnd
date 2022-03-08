import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import RaceFactory, AbilityScoreIncreaseFactory, TraitFactory
from character.tests.factories import LanguageFactory
from .utils import CompareMixin


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

