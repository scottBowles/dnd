import random
from graphql_jwt.testcases import JSONWebTokenTestCase
from graphql_relay import from_global_id, to_global_id
from django.contrib.auth import get_user_model

from character.models.models import ALIGNMENTS, SIZES
from .factories import RaceFactory, AbilityScoreIncreaseFactory, TraitFactory
from character.tests.factories import LanguageFactory
from .utils import CompareMixin
from ..models import Race


class RaceQueryTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_basic_race_detail_query(self):
        race = RaceFactory()
        race_global_id = to_global_id("RaceNode", race.id)

        response = self.client.execute(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    ageOfAdulthood
                    lifeExpectancy
                    alignment
                    size
                    speed
                }
            }
            """
            % race_global_id
        )
        self.assertIsNone(response.errors)

        res_race = response.data["race"]

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

        response = self.client.execute(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
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
        self.assertIsNone(response.errors)

        res_race = response.data["race"]

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

        response = self.client.execute(
            """
            query {
                race(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    ageOfAdulthood
                    lifeExpectancy
                    alignment
                    size
                    speed
                    baseRace {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
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
                                description
                                imageIds
                                thumbnailId
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
        self.assertIsNone(response.errors)

        res_race = response.data["race"]

        self.compare_races(
            race, res_race, compare_base_races_to_depth=1, compare_subraces=True
        )

    def test_basic_race_list_query(self):
        races = RaceFactory.create_batch(random.randint(0, 3))

        response = self.client.execute(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
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
        self.assertIsNone(response.errors)

        res_races = [edge["node"] for edge in response.data["races"]["edges"]]

        for race in races:
            matching_res_race = next(
                res_race for res_race in res_races if res_race["name"] == race.name
            )
            self.compare_races(race, matching_res_race)

    def test_race_list_query_with_relations(self):
        races = []
        for i in range(random.randint(0, 3)):
            languages = LanguageFactory.create_batch(random.randint(0, 3))
            traits = TraitFactory.create_batch(random.randint(0, 3))
            race = RaceFactory(languages=languages, traits=traits)
            races.append(race)

        response = self.client.execute(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
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
        self.assertIsNone(response.errors)

        res_races = response.data["races"]["edges"]

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

        response = self.client.execute(
            """
            query {
                races {
                    edges {
                        node {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
                            ageOfAdulthood
                            lifeExpectancy
                            alignment
                            size
                            speed
                            baseRace {
                                id
                                name
                                description
                                imageIds
                                thumbnailId
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
                                        description
                                        imageIds
                                        thumbnailId
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
        self.assertIsNone(response.errors)

        res_races = response.data["races"]["edges"]

        for i, race in enumerate(all_races):
            self.compare_races(
                race,
                res_races[i]["node"],
                compare_base_races_to_depth=1,
                compare_subraces=True,
            )


class RaceMutationTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)
        self.name = "Test Race Name"
        self.description = "Test Race Description"
        self.image_ids = [
            "Test Race Image Id 1",
            "Test Race Image Id 2",
            "Test Race Image Id 3",
        ]
        self.thumbnail_id = "Test Race Thumbnail Id"
        self.age_of_adulthood = 18
        self.life_expectancy = 99
        self.alignment = ALIGNMENTS[0][0]
        self.size = SIZES[0][0]
        self.speed = 30

    def test_basic_race_create_mutation(self):
        query = """
            mutation RaceCreate($name: String!, $description: String, $imageIds: [String], $thumbnailId: String, $ageOfAdulthood: Int,$lifeExpectancy: Int,$alignment: String,$size: String,$speed: Int) {
                raceCreate(input: {
                    name: $name,
                    description: $description,
                    imageIds: $imageIds,
                    thumbnailId: $thumbnailId,
                    ageOfAdulthood: $ageOfAdulthood,
                    lifeExpectancy: $lifeExpectancy,
                    alignment: $alignment,
                    size: $size,
                    speed: $speed,
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
                    }
                }
            }
        """
        variables = {
            "name": self.name,
            "description": self.description,
            "imageIds": self.image_ids,
            "thumbnailId": self.thumbnail_id,
            "ageOfAdulthood": self.age_of_adulthood,
            "lifeExpectancy": self.life_expectancy,
            "alignment": self.alignment,
            "size": self.size,
            "speed": self.speed,
        }

        response = self.client.execute(query, variables)
        self.assertIsNone(response.errors)

        res_race = response.data["raceCreate"]["race"]

        self.assertEqual(res_race["name"], self.name)
        self.assertEqual(res_race["description"], self.description)
        self.assertEqual(res_race["imageIds"], self.image_ids)
        self.assertEqual(res_race["thumbnailId"], self.thumbnail_id)
        self.assertEqual(res_race["ageOfAdulthood"], self.age_of_adulthood)
        self.assertEqual(res_race["lifeExpectancy"], self.life_expectancy)
        self.assertEqual(res_race["alignment"], self.alignment)
        self.assertEqual(res_race["size"], self.size)
        self.assertEqual(res_race["speed"], self.speed)

        created_race = Race.objects.first()
        self.assertEqual(str(created_race.id), from_global_id(res_race["id"])[1])
        self.assertEqual(created_race.name, self.name)
        self.assertEqual(created_race.description, self.description)
        self.assertEqual(created_race.image_ids, self.image_ids)
        self.assertEqual(created_race.thumbnail_id, self.thumbnail_id)
        self.assertEqual(created_race.age_of_adulthood, self.age_of_adulthood)
        self.assertEqual(created_race.life_expectancy, self.life_expectancy)
        self.assertEqual(created_race.alignment, self.alignment)
        self.assertEqual(created_race.size, self.size)
        self.assertEqual(created_race.speed, self.speed)

        self.compare_races(created_race, res_race)

    def test_race_create_with_base_and_subraces(self):
        base_race = RaceFactory()
        subraces = RaceFactory.create_batch(2)
        query = """
            mutation RaceCreate($name: String!, $description: String, $imageIds: [String], $thumbnailId: String, $ageOfAdulthood: Int,$lifeExpectancy: Int,$alignment: String,$size: String,$speed: Int,$baseRace: String,$subraces: [String]) {
                raceCreate(input: {
                    name: $name,
                    description: $description,
                    imageIds: $imageIds,
                    thumbnailId: $thumbnailId,
                    ageOfAdulthood: $ageOfAdulthood,
                    lifeExpectancy: $lifeExpectancy,
                    alignment: $alignment,
                    size: $size,
                    speed: $speed,
                    baseRace: $baseRace,
                    subraces: $subraces,
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
                        baseRace {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
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
                                    description
                                    imageIds
                                    thumbnailId
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
        """
        variables = {
            "name": self.name,
            "description": self.description,
            "imageIds": self.image_ids,
            "thumbnailId": self.thumbnail_id,
            "ageOfAdulthood": self.age_of_adulthood,
            "lifeExpectancy": self.life_expectancy,
            "alignment": self.alignment,
            "size": self.size,
            "speed": self.speed,
            "baseRace": to_global_id("RaceNode", base_race.id),
            "subraces": [
                to_global_id("RaceNode", subraces[0].id),
                to_global_id("RaceNode", subraces[1].id),
            ],
        }

        response = self.client.execute(query, variables)
        self.assertIsNone(response.errors)

        res_race = response.data["raceCreate"]["race"]
        created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        self.compare_races(
            created_race, res_race, compare_subraces=True, compare_base_races_to_depth=1
        )

    def test_race_create_with_adding_existing_languages(self):
        language1 = LanguageFactory()
        language2 = LanguageFactory()

        query = """
            mutation {
                raceCreate(input: {
                    name: "%s",
                    description: "%s",
                    imageIds: "%s",
                    thumbnailId: "%s",
                    ageOfAdulthood: %s,
                    lifeExpectancy: %s,
                    alignment: "%s",
                    size: "%s",
                    speed: %s,
                    languages: ["%s", "%s"]
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
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
                    }
                }
            }
        """ % (
            self.name,
            self.description,
            self.image_ids,
            self.thumbnail_id,
            self.age_of_adulthood,
            self.life_expectancy,
            self.alignment,
            self.size,
            self.speed,
            to_global_id("LanguageNode", language1.id),
            to_global_id("LanguageNode", language2.id),
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_race = response.data["raceCreate"]["race"]

        created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        self.assertEqual(len(created_race.languages.all()), 2)
        self.compare_races(created_race, res_race, compare_languages=True)

    def test_race_create_fails_with_nonexisting_language_ids(self):
        query = """
            mutation {
                raceCreate(input: {
                    name: "%s",
                    description: "%s",
                    imageIds: "%s",
                    thumbnailId: "%s",
                    ageOfAdulthood: %s,
                    lifeExpectancy: %s,
                    alignment: "%s",
                    size: "%s",
                    speed: %s,
                    languages: ["%s", "%s"]
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        image_ids
                        thumbnail_id
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
                    }
                }
            }
        """ % (
            self.name,
            self.description,
            self.image_ids,
            self.thumbnail_id,
            self.age_of_adulthood,
            self.life_expectancy,
            self.alignment,
            self.size,
            self.speed,
            to_global_id("LanguageNode", 23456),
            to_global_id("LanguageNode", 12345),
        )

        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

        with self.assertRaises(Race.DoesNotExist):
            Race.objects.get(name="Test Race Name")

    def test_race_create_with_adding_existing_traits(self):
        trait1 = TraitFactory()
        trait2 = TraitFactory()

        query = """
            mutation {
                raceCreate(input: {
                    name: "%s",
                    description: "%s",
                    imageIds: "%s",
                    thumbnailId: "%s",
                    ageOfAdulthood: %s,
                    lifeExpectancy: %s,
                    alignment: "%s",
                    size: "%s",
                    speed: %s,
                    traits: ["%s", "%s"]
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
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
        """ % (
            self.name,
            self.description,
            self.image_ids,
            self.thumbnail_id,
            self.age_of_adulthood,
            self.life_expectancy,
            self.alignment,
            self.size,
            self.speed,
            to_global_id("TraitNode", trait1.id),
            to_global_id("TraitNode", trait2.id),
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_race = response.data["raceCreate"]["race"]

        created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        self.assertEqual(len(created_race.traits.all()), 2)
        self.compare_races(created_race, res_race, compare_traits=True)

    def test_race_create_fails_with_nonexisting_trait_ids(self):
        query = """
            mutation {
                raceCreate(input: {
                    name: "%s",
                    description: "%s",
                    imageIds: "%s",
                    thumbnailId: "%s",
                    ageOfAdulthood: %s,
                    lifeExpectancy: %s,
                    alignment: "%s",
                    size: "%s",
                    speed: %s,
                    traits: ["%s", "%s"]
                }) {
                    ok
                    errors
                    race {
                        id
                        name
                        description
                        image_ids
                        thumbnail_id
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
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
        """ % (
            self.name,
            self.description,
            self.image_ids,
            self.thumbnail_id,
            self.age_of_adulthood,
            self.life_expectancy,
            self.alignment,
            self.size,
            self.speed,
            to_global_id("TraitNode", 23456),
            to_global_id("TraitNode", 12345),
        )

        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

        with self.assertRaises(Race.DoesNotExist):
            Race.objects.get(name="Test Race Name")

        # def test_race_create_with_adding_existing_AbilityScoreIncreases(self):
        #     asis = AbilityScoreIncreaseFactory.create_batch(8)
        #     asis = list(set(asis))
        #     asis.sort(key=lambda x: x.id)
        #     asi_global_ids = ", ".join(
        #         [str(to_global_id("AbilityScoreIncreaseNode", asi.id)) for asi in asis]
        #     )

        #     query = """
        #         mutation {
        #             raceCreate(input: {
        #                 name: "%s",
        #                 ageOfAdulthood: %s,
        #                 lifeExpectancy: %s,
        #                 alignment: "%s",
        #                 size: "%s",
        #                 speed: %s,
        #                 abilityScoreIncreases: "%s"
        #             }) {
        #                 ok
        #                 errors
        #                 race {
        #                     id
        #                     name
        #                     ageOfAdulthood
        #                     lifeExpectancy
        #                     alignment
        #                     size
        #                     speed
        #                     abilityScoreIncreases {
        #                         edges {
        #                             node {
        #                                 id
        #                                 abilityScore
        #                                 increase
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     """ % (
        #         self.name,
        #         self.age_of_adulthood,
        #         self.life_expectancy,
        #         self.alignment,
        #         self.size,
        #         self.speed,
        #         f"{asi_global_ids}",
        #         # to_global_id("AbilityScoreIncreaseNode", ability_score_increase_1.id),
        #         # to_global_id("AbilityScoreIncreaseNode", ability_score_increase_2.id),
        #     )

        #     response = self.client.execute(query)
        #     self.assertIsNone(response.errors)

        #
        #     res_race = response.data["raceCreate"]["race"]

        #     created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        #     self.assertEqual(len(created_race.ability_score_increases.all()), len(asis))
        #     self.compare_races(created_race, res_race, compare_ability_score_increases=True)

        # def test_race_create_fails_with_nonexisting_ability_score_increase_ids(self):
        #     query = """
        #         mutation {
        #             raceCreate(input: {
        #                 name: "%s",
        #                 ageOfAdulthood: %s,
        #                 lifeExpectancy: %s,
        #                 alignment: "%s",
        #                 size: "%s",
        #                 speed: %s,
        #                 abilityScoreIncreases: ["%s", "%s"]
        #             }) {
        #                 ok
        #                 errors
        #                 race {
        #                     id
        #                     name
        #                     ageOfAdulthood
        #                     lifeExpectancy
        #                     alignment
        #                     size
        #                     speed
        #                     abilityScoreIncreases {
        #                         edges {
        #                             node {
        #                                 id
        #                                 abilityScore
        #                                 increase
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     """ % (
        #         self.name,
        #         self.age_of_adulthood,
        #         self.life_expectancy,
        #         self.alignment,
        #         self.size,
        #         self.speed,
        #         to_global_id("AbilityScoreIncreaseNode", 23456),
        #         to_global_id("AbilityScoreIncreaseNode", 12345),
        #     )

        #     response = self.client.execute(query)
        #     self.assertIsNotNone(response.errors)

        #     with self.assertRaises(Race.DoesNotExist):
        #         Race.objects.get(name="Test Race Name")

        #     def test_race_create_with_adding_existing_associations(self):
        #         association1 = AssociationFactory()
        #         association2 = AssociationFactory()

        #         query = """
        #             mutation {
        #                 raceCreate(input: {
        #                     name: "Test Race Name"
        #                     description: "Test Race Description"
        #                     raceType: "TOWN"
        #                     population: 100
        #                     associations: [{
        #                         notes: "Test Notes 1"
        #                         association: "%s"
        #                     }, {
        #                         notes: "Test Notes 2"
        #                         association: "%s"
        #                     }]
        #                 }) {
        #                     ok
        #                     errors
        #                     race {
        #                         id
        #                         name
        #                         description
        #                         created
        #                         updated
        #                         raceType
        #                         population
        #                         associations {
        #                             edges {
        #                                 notes
        #                                 node {
        #                                     id
        #                                     name
        #                                     description
        #                                 }
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         """ % (
        #             to_global_id("AssociationNode", association1.id),
        #             to_global_id("AssociationNode", association2.id),
        #         )

        #         response = self.client.execute(query)
        #         self.assertIsNone(response.errors)

        #
        #         res_race = response.data["raceCreate"]["race"]

        #         created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        #         self.assertEqual(len(created_race.associations.all()), 2)
        #         self.compare_races(created_race, res_race, compare_associations=True)

        #     def test_race_create_fails_with_nonexisting_association_ids(self):
        #         query = """
        #             mutation {
        #                 raceCreate(input: {
        #                     name: "Test Race Name"
        #                     description: "Test Race Description"
        #                     raceType: "TOWN"
        #                     population: 100
        #                     associations: [{
        #                         significance: 0
        #                         association: "%s"
        #                     }, {
        #                         significance: 1
        #                         association: "%s"
        #                     }]
        #                 }) {
        #                     ok
        #                     errors
        #                     race {
        #                         id
        #                         name
        #                         description
        #                         created
        #                         updated
        #                         raceType
        #                         population
        #                         associations {
        #                             edges {
        #                                 notes
        #                                 node {
        #                                     id
        #                                     name
        #                                     description
        #                                 }
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         """ % (
        #             to_global_id("AssociationNode", 23456),
        #             to_global_id("AssociationNode", 12345),
        #         )

        #         response = self.client.execute(query)
        #         self.assertIsNotNone(response.errors)

        #         with self.assertRaises(Race.DoesNotExist):
        #             Race.objects.get(name="Test Race Name")

        # ASSOCIATIONS AND RACES REMAIN

        # def test_association_create_with_common_races(self):
        #     query = """
        #         mutation {
        #             raceCreate(input: {
        #                 name: "Test Race Name"
        #                 description: "Test Race Description"
        #                 raceType: "TOWN"
        #                 population: 100
        #                 commonRaces: [{
        #                     significance: 0
        #                     export: {
        #                         name: "Nitre"
        #                         description: "Salt from the desert"
        #                     }
        #                 }, {
        #                     significance: 1
        #                     export: {
        #                         name: "Wheat"
        #                         description: "Good for making bread"
        #                     }
        #                 }]
        #             }) {
        #                 ok
        #                 errors
        #                 race {
        #                     id
        #                     name
        #                     description
        #                     created
        #                     updated
        #                     raceType
        #                     population
        #                     exports {
        #                         edges {
        #                             significance
        #                             node {
        #                                 id
        #                                 name
        #                                 description
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     """

        #     response = self.client.execute(query)
        #     self.assertIsNone(response.errors)

        #
        #     res_race = response.data["raceCreate"]["race"]

        #     created_race = Race.objects.get(pk=from_global_id(res_race["id"])[1])

        #     self.assertEqual(len(created_race.exports.all()), 2)
        #     self.compare_races(created_race, res_race, compare_exports=True)

        # def test_association_update_mutation(self):
        #     association = AssociationFactory(
        #         name="Not Test Assoc Name", description="Not Test Assoc Description"
        #     )
        #     association_global_id = to_global_id("AssociationNode", association.id)
        #     query = (
        #         """
        #         mutation {
        #             associationUpdate(input: {
        #                 id: "%s"
        #                 name: "Test Assoc Name"
        #                 description: "Test Assoc Description"
        #             }) {
        #                 association {
        #                     id
        #                     name
        #                     description
        #                 }
        #             }
        #         }
        #     """
        #         % association_global_id
        #     )
        #     response = self.client.execute(query)
        #     self.assertIsNone(response.errors)

        #
        #     res_association = response.data["associationUpdate"]["association"]

        #     self.assertEqual(res_association["name"], "Test Assoc Name")
        #     self.assertEqual(res_association["description"], "Test Assoc Description")

        #     updated_association = Association.objects.get(
        #         pk=from_global_id(res_association["id"])[1]
        #     )
        #     self.assertEqual(updated_association.name, "Test Assoc Name")
        #     self.assertEqual(updated_association.description, "Test Assoc Description")

        # def test_association_update_bad_input_no_id(self):
        #     AssociationFactory()
        #     query = """
        #         mutation {
        #             associationUpdate(input: {
        #                 name: "Test Assoc Name"
        #                 description: "Test Assoc Description"
        #             }) {
        #                 association {
        #                     id
        #                     name
        #                     description
        #                 }
        #             }
        #         }
        #     """
        #     response = self.client.execute(query)
        #     self.assertIsNotNone(response.errors)

        # def test_association_update_bad_input_no_name(self):
        #     association = AssociationFactory()
        #     association_global_id = to_global_id("AssociationNode", association.id)
        #     query = (
        #         """
        #         mutation {
        #             associationUpdate(input: {
        #                 id: "%s"
        #                 description: "Test Assoc Description"
        #             }) {
        #                 association {
        #                     id
        #                     name
        #                     description
        #                 }
        #             }
        #         }
        #     """
        #         % association_global_id
        #     )
        #     response = self.client.execute(query)
        #     self.assertIsNotNone(response.errors)

        # def test_association_patch(self):
        #     association = AssociationFactory(
        #         name="Not Test Assoc Name", description="Test Assoc Description"
        #     )
        #     association_global_id = to_global_id("AssociationNode", association.id)
        #     query = (
        #         """
        #         mutation {
        #             associationPatch(input: {
        #                 id: "%s"
        #                 name: "Test Assoc Name"
        #             }) {
        #                 association {
        #                     id
        #                     name
        #                     description
        #                 }
        #             }
        #         }
        #     """
        #         % association_global_id
        #     )
        #     response = self.client.execute(query)
        #     self.assertIsNone(response.errors)

        #
        #     res_association = response.data["associationPatch"]["association"]
        #     self.assertEqual(res_association["name"], "Test Assoc Name")
        #     self.assertEqual(res_association["description"], "Test Assoc Description")

        # def test_association_patch_null_name(self):
        #     association = AssociationFactory(
        #         name="Not Test Assoc Name", description="Test Assoc Description"
        #     )
        #     association_global_id = to_global_id("AssociationNode", association.id)
        #     query = (
        #         """
        #         mutation {
        #             associationPatch(input: {
        #                 id: "%s"
        #                 name: null
        #             }) {
        #                 association {
        #                     id
        #                     name
        #                     description
        #                 }
        #             }
        #         }
        #     """
        #         % association_global_id
        #     )
        #     response = self.client.execute(query)
        #     self.assertIsNotNone(response.errors)


# def test_association_delete(self):
#     association = AssociationFactory()
#     association_global_id = to_global_id("AssociationNode", association.id)
#     query = (
#         """
#         mutation {
#             associationDelete(input: {
#                 id: "%s"
#             }) {
#                 ok
#             }
#         }
#     """
#         % association_global_id
#     )
#     response = self.client.execute(query)
#     self.assertIsNone(response.errors)

#
#     self.assertTrue(response.data["associationDelete"]["ok"])

#     with self.assertRaises(Association.DoesNotExist):
#         Association.objects.get(pk=association.id)
