import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import from_global_id, to_global_id
from .factories import (
    NPCFactory,
    FeatureFactory,
    SkillFactory,
    ProficiencyFactory,
)
from race.tests.factories import RaceFactory
from .utils import CompareMixin


class NPCQueryTests(CompareMixin, GraphQLTestCase):
    def test_basic_npc_detail_query(self):
        npc = NPCFactory()
        response = self.query(
            """
            query {
                npc(id: "%s") {
                    id
                    name
                    description
                    size
                    race {
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
            """
            % to_global_id("NPCNode", npc.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_npc = res_json["data"]["npc"]
        self.compare_npcs(npc, res_npc)

    def test_npc_detail_query_with_relations(self):
        race = RaceFactory()
        features = FeatureFactory.create_batch(random.randint(1, 4))
        proficiencies = ProficiencyFactory.create_batch(random.randint(1, 4))

        npc = NPCFactory(
            race=race, features_and_traits=features, proficiencies=proficiencies
        )

        response = self.query(
            """
            query {
                npc(id: "%s") {
                    id
                    name
                    description
                    size
                    race {
                        id
                        name
                        ageOfAdulthood
                        lifeExpectancy
                        alignment
                        size
                        speed
                    }
                    featuresAndTraits {
                        edges {
                            node {
                                id
                                name
                                description
                            }
                        }
                    }
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
            }
            """
            % to_global_id("NPCNode", npc.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_npc = res_json["data"]["npc"]
        self.assertGreater(len(res_npc["featuresAndTraits"]["edges"]), 0)
        self.assertGreater(len(res_npc["proficiencies"]["edges"]), 0)
        self.compare_npcs(
            npc, res_npc, compare_features=True, compare_proficiencies=True
        )


class FeatureTests(CompareMixin, GraphQLTestCase):
    def test_feature_detail_query(self):
        feature = FeatureFactory()
        response = self.query(
            """
            query {
                feature(id: "%s") {
                    id
                    name
                    description
                }
            }
            """
            % to_global_id("FeatureNode", feature.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_feature = res_json["data"]["feature"]
        self.compare_features(feature, res_feature)

    def test_feature_list_query(self):
        num_features = random.randint(0, 10)
        features = FeatureFactory.create_batch(num_features)
        response = self.query(
            """
            query {
                features {
                    edges {
                        node {
                            id
                            name
                            description
                        }
                    }
                }
            }
            """
        )
        self.assertResponseNoErrors(response)
        res_json = json.loads(response.content)
        res_features = res_json["data"]["features"]["edges"]
        self.assertEqual(len(res_features), num_features)
        for i, feature in enumerate(features):
            res_feature = res_features[i]["node"]
            self.compare_features(feature, res_feature)


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


class ProficiencyTests(CompareMixin, GraphQLTestCase):
    def test_proficiency_detail_query(self):
        proficiency = ProficiencyFactory()
        response = self.query(
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
            % to_global_id("ProficiencyNode", proficiency.id)
        )
        self.assertResponseNoErrors(response)

        res_json = json.loads(response.content)
        res_proficiency = res_json["data"]["proficiency"]
        self.compare_proficiencies(proficiency, res_proficiency)

    def test_proficiency_list_query(self):
        num_proficiencies = random.randint(0, 10)
        proficiencies = ProficiencyFactory.create_batch(num_proficiencies)
        response = self.query(
            """
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
        )
        self.assertResponseNoErrors(response)
        res_json = json.loads(response.content)
        res_proficiencies = res_json["data"]["proficiencies"]["edges"]
        self.assertEqual(len(res_proficiencies), num_proficiencies)
        for i, proficiency in enumerate(proficiencies):
            res_proficiency = res_proficiencies[i]["node"]
            self.compare_proficiencies(proficiency, res_proficiency)


# class PlaceQueryTests(CompareMixin, GraphQLTestCase):
#     def test_basic_place_list_query(self):
#         places = PlaceFactory.create_batch(2)

#         response = self.query(
#             """
#             query {
#                 places {
#                     edges {
#                         node {
#                             id
#                             name
#                             description
#                             created
#                             updated
#                             placeType
#                             population
#                         }
#                     }
#                 }
#             }
#             """
#         )
#         self.assertResponseNoErrors(response)
#         res_places = json.loads(response.content)
#         res_places = res_places["data"]["places"]["edges"]

#         self.assertEqual(len(res_places), 2)
#         for i, place in enumerate(places):
#             equivalent_place = res_places[i]["node"]
#             self.assertEqual(str(place.id), from_global_id(equivalent_place["id"])[1])
#             self.assertEqual(place.name, equivalent_place["name"])
#             self.assertEqual(place.description, equivalent_place["description"])
#             self.assertEqual(place.place_type, equivalent_place["placeType"])
#             self.assertEqual(place.population, equivalent_place["population"])

#     def test_place_list_query(self):
#         place_great_grandparent = PlaceFactory()
#         place_grandparent = PlaceFactory(parent=place_great_grandparent)
#         place_parent = PlaceFactory(parent=place_grandparent)
#         place = PlaceFactory(parent=place_parent)
#         places = Place.objects.all()

#         response = self.query(
#             """
#             query {
#                 places {
#                     edges {
#                         node {
#                             id
#                             name
#                             description
#                             created
#                             updated
#                             placeType
#                             population
#                             parent {
#                                 id
#                                 name
#                                 description
#                                 created
#                                 updated
#                                 placeType
#                                 population
#                                 parent {
#                                     id
#                                     name
#                                     description
#                                     created
#                                     updated
#                                     placeType
#                                     population
#                                 }
#                             }
#                         }
#                     }
#                 }
#             }
#             """
#         )
#         self.assertResponseNoErrors(response)
#         result = json.loads(response.content)
#         self.assertEqual(len(result["data"]["places"]["edges"]), places.count())
#         for i, place in enumerate(places):
#             equivalent_place = result["data"]["places"]["edges"][i]["node"]
#             self.compare_places(place, equivalent_place, compare_parents_to_depth=2)

#     def test_basic_place_detail_query(self):
#         place = PlaceFactory()

#         response = self.query(
#             """
#             query {
#                 place(id: "%s") {
#                     id
#                     name
#                     description
#                     created
#                     updated
#                     placeType
#                     population
#                 }
#             }
#             """
#             % to_global_id("PlaceNode", place.id)
#         )
#         self.assertResponseNoErrors(response)

#         res_json = json.loads(response.content)
#         res_place = res_json["data"]["place"]

#         self.compare_places(place, res_place)

#     def test_place_detail_query_with_parents(self):
#         place_greatgrandparent = PlaceFactory(name="place_greatgrandparent")
#         place_grandparent = PlaceFactory(
#             parent=place_greatgrandparent, name="place_grandparent"
#         )
#         place_parent = PlaceFactory(parent=place_grandparent, name="place_parent")
#         place_child = PlaceFactory(parent=place_parent, name="place_child")

#         response = self.query(
#             """
#             query {
#                 place(id: "%s") {
#                     id
#                     name
#                     description
#                     created
#                     updated
#                     placeType
#                     population
#                     parent {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                         parent {
#                             id
#                             name
#                             description
#                             created
#                             updated
#                             placeType
#                             population
#                         }
#                     }
#                 }
#             }
#             """
#             % to_global_id("PlaceNode", place_child.id)
#         )
#         self.assertResponseNoErrors(response)

#         res_place = json.loads(response.content)
#         res_place = res_place["data"]["place"]

#         self.compare_places(place_child, res_place, compare_parents_to_depth=2)

#     def test_place_detail_query_with_m2m_associations(self):
#         place1 = PlaceFactory()
#         place2 = PlaceFactory()
#         association1 = AssociationFactory()
#         association2 = AssociationFactory()
#         PlaceAssociationFactory(place=place1, association=association1)
#         PlaceAssociationFactory(place=place1, association=association2)
#         PlaceAssociationFactory(place=place2, association=association1)
#         PlaceAssociationFactory(place=place2, association=association2)

#         response = self.query(
#             """
#             query {
#                 place(id: "%s") {
#                     id
#                     name
#                     description
#                     created
#                     updated
#                     placeType
#                     population
#                     associations {
#                         edges {
#                             notes
#                             node {
#                                 id
#                                 name
#                                 description
#                             }
#                         }
#                     }
#                 }
#             }
#             """
#             % to_global_id("PlaceNode", place1.id)
#         )
#         self.assertResponseNoErrors(response)

#         res_json = json.loads(response.content)
#         res_place = res_json["data"]["place"]

#         self.assertEqual(len(res_place["associations"]["edges"]), 2)
#         self.compare_places(place1, res_place, compare_associations=True)

#     def test_place_detail_query_with_m2m_exports(self):
#         place1 = PlaceFactory()
#         place2 = PlaceFactory()
#         export1 = ExportFactory()
#         export2 = ExportFactory()
#         PlaceExportFactory(place=place1, export=export1)
#         PlaceExportFactory(place=place1, export=export2)
#         PlaceExportFactory(place=place2, export=export1)
#         PlaceExportFactory(place=place2, export=export2)

#         response = self.query(
#             """
#             query {
#                 place(id: "%s") {
#                     id
#                     name
#                     description
#                     created
#                     updated
#                     placeType
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
#             """
#             % to_global_id("PlaceNode", place1.id)
#         )
#         self.assertResponseNoErrors(response)

#         res_json = json.loads(response.content)
#         res_place = res_json["data"]["place"]

#         self.assertEqual(len(res_place["exports"]["edges"]), 2)
#         self.compare_places(place1, res_place, compare_exports=True)

#     def test_place_detail_query_with_m2m_races(self):
#         place1 = PlaceFactory()
#         place2 = PlaceFactory()
#         race1 = RaceFactory()
#         race2 = RaceFactory()
#         PlaceRaceFactory(place=place1, race=race1)
#         PlaceRaceFactory(place=place1, race=race2)
#         PlaceRaceFactory(place=place2, race=race1)
#         PlaceRaceFactory(place=place2, race=race2)

#         response = self.query(
#             """
#             query {
#                 place(id: "%s") {
#                     id
#                     name
#                     description
#                     created
#                     updated
#                     placeType
#                     population
#                     commonRaces {
#                         edges {
#                             percent
#                             notes
#                             node {
#                                 id
#                                 name
#                             }
#                         }
#                     }
#                 }
#             }
#             """
#             % to_global_id("PlaceNode", place1.id)
#         )
#         self.assertResponseNoErrors(response)

#         res_json = json.loads(response.content)
#         res_place = res_json["data"]["place"]

#         self.assertEqual(len(res_place["commonRaces"]["edges"]), 2)
#         self.compare_places(place1, res_place, compare_races=True)


# class PlaceMutationTests(CompareMixin, GraphQLTestCase):
#     def test_basic_place_create_mutation(self):
#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
#                     population: 100
#                 }) {
#                     ok
#                     errors
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                     }
#                 }
#             }
#         """
#         response = self.query(query)
#         self.assertResponseNoErrors(response)

#         result = json.loads(response.content)
#         res_place = result["data"]["placeCreate"]["place"]

#         self.assertEqual(res_place["name"], "Test Place Name")
#         self.assertEqual(res_place["description"], "Test Place Description")

#         created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])
#         self.assertEqual(created_place.name, "Test Place Name")
#         self.assertEqual(created_place.description, "Test Place Description")

#         self.compare_places(created_place, res_place)

#     def test_place_create_bad_input(self):  # (no `name` value provided)
#         query = """
#             mutation {
#                 placeCreate(input: {
#                     description: "Test Place Description"
#                 }) {
#                     ok
#                     errors
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                     }
#                 }
#             }
#         """
#         response = self.query(query)
#         self.assertResponseHasErrors(response)

#     def test_place_create_with_parent(self):
#         parent = PlaceFactory()
#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
#                     population: 100
#                     parent: {
#                         id: "%s"
#                     }
#                 }) {
#                     ok
#                     errors
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                         parent {
#                             id
#                             name
#                             description
#                             created
#                             updated
#                             placeType
#                             population
#                         }
#                     }
#                 }
#             }
#         """ % to_global_id(
#             "PlaceNode", parent.id
#         )

#         response = self.query(query)
#         self.assertResponseNoErrors(response)

#         result = json.loads(response.content)
#         res_place = result["data"]["placeCreate"]["place"]

#         created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

#         self.compare_places(created_place, res_place, compare_parents_to_depth=1)

#     def test_place_create_with_adding_existing_exports(self):
#         export1 = ExportFactory()
#         export2 = ExportFactory()

#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
#                     population: 100
#                     exports: [{
#                         significance: 0
#                         export: "%s"
#                     }, {
#                         significance: 1
#                         export: "%s"
#                     }]
#                 }) {
#                     ok
#                     errors
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                         exports {
#                             edges {
#                                 significance
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
#             to_global_id("ExportNode", export1.id),
#             to_global_id("ExportNode", export2.id),
#         )

#         response = self.query(query)
#         self.assertResponseNoErrors(response)

#         result = json.loads(response.content)
#         res_place = result["data"]["placeCreate"]["place"]

#         created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

#         self.assertEqual(len(created_place.exports.all()), 2)
#         self.compare_places(created_place, res_place, compare_exports=True)

#     def test_place_create_fails_with_nonexisting_export_ids(self):
#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
#                     population: 100
#                     exports: [{
#                         significance: 0
#                         export: "%s"
#                     }, {
#                         significance: 1
#                         export: "%s"
#                     }]
#                 }) {
#                     ok
#                     errors
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
#                         population
#                         exports {
#                             edges {
#                                 significance
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
#             to_global_id("ExportNode", 23456),
#             to_global_id("ExportNode", 12345),
#         )

#         response = self.query(query)
#         self.assertResponseHasErrors(response)

#         with self.assertRaises(Place.DoesNotExist):
#             Place.objects.get(name="Test Place Name")

#     def test_place_create_with_adding_existing_associations(self):
#         association1 = AssociationFactory()
#         association2 = AssociationFactory()

#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
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
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
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

#         response = self.query(query)
#         self.assertResponseNoErrors(response)

#         result = json.loads(response.content)
#         res_place = result["data"]["placeCreate"]["place"]

#         created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

#         self.assertEqual(len(created_place.associations.all()), 2)
#         self.compare_places(created_place, res_place, compare_associations=True)

#     def test_place_create_fails_with_nonexisting_association_ids(self):
#         query = """
#             mutation {
#                 placeCreate(input: {
#                     name: "Test Place Name"
#                     description: "Test Place Description"
#                     placeType: "TOWN"
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
#                     place {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                         placeType
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

#         response = self.query(query)
#         self.assertResponseHasErrors(response)

#         with self.assertRaises(Place.DoesNotExist):
#             Place.objects.get(name="Test Place Name")

#     # ASSOCIATIONS AND RACES REMAIN

#     # def test_association_create_with_common_races(self):
#     #     query = """
#     #         mutation {
#     #             placeCreate(input: {
#     #                 name: "Test Place Name"
#     #                 description: "Test Place Description"
#     #                 placeType: "TOWN"
#     #                 population: 100
#     #                 commonRaces: [{
#     #                     significance: 0
#     #                     export: {
#     #                         name: "Nitre"
#     #                         description: "Salt from the desert"
#     #                     }
#     #                 }, {
#     #                     significance: 1
#     #                     export: {
#     #                         name: "Wheat"
#     #                         description: "Good for making bread"
#     #                     }
#     #                 }]
#     #             }) {
#     #                 ok
#     #                 errors
#     #                 place {
#     #                     id
#     #                     name
#     #                     description
#     #                     created
#     #                     updated
#     #                     placeType
#     #                     population
#     #                     exports {
#     #                         edges {
#     #                             significance
#     #                             node {
#     #                                 id
#     #                                 name
#     #                                 description
#     #                             }
#     #                         }
#     #                     }
#     #                 }
#     #             }
#     #         }
#     #     """

#     #     response = self.query(query)
#     #     self.assertResponseNoErrors(response)

#     #     result = json.loads(response.content)
#     #     res_place = result["data"]["placeCreate"]["place"]

#     #     created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

#     #     self.assertEqual(len(created_place.exports.all()), 2)
#     #     self.compare_places(created_place, res_place, compare_exports=True)

#     # def test_association_update_mutation(self):
#     #     association = AssociationFactory(
#     #         name="Not Test Assoc Name", description="Not Test Assoc Description"
#     #     )
#     #     association_global_id = to_global_id("AssociationNode", association.id)
#     #     query = (
#     #         """
#     #         mutation {
#     #             associationUpdate(input: {
#     #                 id: "%s"
#     #                 name: "Test Assoc Name"
#     #                 description: "Test Assoc Description"
#     #             }) {
#     #                 association {
#     #                     id
#     #                     name
#     #                     description
#     #                 }
#     #             }
#     #         }
#     #     """
#     #         % association_global_id
#     #     )
#     #     response = self.query(query)
#     #     self.assertResponseNoErrors(response)

#     #     result = json.loads(response.content)
#     #     res_association = result["data"]["associationUpdate"]["association"]

#     #     self.assertEqual(res_association["name"], "Test Assoc Name")
#     #     self.assertEqual(res_association["description"], "Test Assoc Description")

#     #     updated_association = Association.objects.get(
#     #         pk=from_global_id(res_association["id"])[1]
#     #     )
#     #     self.assertEqual(updated_association.name, "Test Assoc Name")
#     #     self.assertEqual(updated_association.description, "Test Assoc Description")

#     # def test_association_update_bad_input_no_id(self):
#     #     AssociationFactory()
#     #     query = """
#     #         mutation {
#     #             associationUpdate(input: {
#     #                 name: "Test Assoc Name"
#     #                 description: "Test Assoc Description"
#     #             }) {
#     #                 association {
#     #                     id
#     #                     name
#     #                     description
#     #                 }
#     #             }
#     #         }
#     #     """
#     #     response = self.query(query)
#     #     self.assertResponseHasErrors(response)

#     # def test_association_update_bad_input_no_name(self):
#     #     association = AssociationFactory()
#     #     association_global_id = to_global_id("AssociationNode", association.id)
#     #     query = (
#     #         """
#     #         mutation {
#     #             associationUpdate(input: {
#     #                 id: "%s"
#     #                 description: "Test Assoc Description"
#     #             }) {
#     #                 association {
#     #                     id
#     #                     name
#     #                     description
#     #                 }
#     #             }
#     #         }
#     #     """
#     #         % association_global_id
#     #     )
#     #     response = self.query(query)
#     #     self.assertResponseHasErrors(response)

#     # def test_association_patch(self):
#     #     association = AssociationFactory(
#     #         name="Not Test Assoc Name", description="Test Assoc Description"
#     #     )
#     #     association_global_id = to_global_id("AssociationNode", association.id)
#     #     query = (
#     #         """
#     #         mutation {
#     #             associationPatch(input: {
#     #                 id: "%s"
#     #                 name: "Test Assoc Name"
#     #             }) {
#     #                 association {
#     #                     id
#     #                     name
#     #                     description
#     #                 }
#     #             }
#     #         }
#     #     """
#     #         % association_global_id
#     #     )
#     #     response = self.query(query)
#     #     self.assertResponseNoErrors(response)

#     #     result = json.loads(response.content)
#     #     res_association = result["data"]["associationPatch"]["association"]
#     #     self.assertEqual(res_association["name"], "Test Assoc Name")
#     #     self.assertEqual(res_association["description"], "Test Assoc Description")

#     # def test_association_patch_null_name(self):
#     #     association = AssociationFactory(
#     #         name="Not Test Assoc Name", description="Test Assoc Description"
#     #     )
#     #     association_global_id = to_global_id("AssociationNode", association.id)
#     #     query = (
#     #         """
#     #         mutation {
#     #             associationPatch(input: {
#     #                 id: "%s"
#     #                 name: null
#     #             }) {
#     #                 association {
#     #                     id
#     #                     name
#     #                     description
#     #                 }
#     #             }
#     #         }
#     #     """
#     #         % association_global_id
#     #     )
#     #     response = self.query(query)
#     #     self.assertResponseHasErrors(response)

#     # def test_association_delete(self):
#     #     association = AssociationFactory()
#     #     association_global_id = to_global_id("AssociationNode", association.id)
#     #     query = (
#     #         """
#     #         mutation {
#     #             associationDelete(input: {
#     #                 id: "%s"
#     #             }) {
#     #                 ok
#     #             }
#     #         }
#     #     """
#     #         % association_global_id
#     #     )
#     #     response = self.query(query)
#     #     self.assertResponseNoErrors(response)

#     #     result = json.loads(response.content)
#     #     self.assertTrue(result["data"]["associationDelete"]["ok"])

#     #     with self.assertRaises(Association.DoesNotExist):
#     #         Association.objects.get(pk=association.id)
