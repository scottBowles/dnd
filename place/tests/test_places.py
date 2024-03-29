from graphql_jwt.testcases import JSONWebTokenTestCase
from ..models import Place, PlaceExport
from graphql_relay import from_global_id, to_global_id
from .factories import (
    PlaceFactory,
    AssociationFactory,
    PlaceAssociationFactory,
    ExportFactory,
    PlaceExportFactory,
    RaceFactory,
    PlaceRaceFactory,
)
from django.contrib.auth import get_user_model


class CompareMixin(JSONWebTokenTestCase):
    def compare_associations(self, model_association, node_association):
        self.assertEqual(
            str(model_association.id), from_global_id(node_association["id"])[1]
        )
        self.assertEqual(model_association.name, node_association["name"])
        self.assertEqual(model_association.description, node_association["description"])

    def compare_place_association_edges(self, place_associations, edges):
        for i, placeassociation in enumerate(place_associations):
            self.assertEqual(placeassociation.notes, edges[i]["notes"])
            self.compare_associations(placeassociation.association, edges[i]["node"])

    def compare_exports(self, model_export, node_export):
        self.assertEqual(str(model_export.id), from_global_id(node_export["id"])[1])
        self.assertEqual(model_export.name, node_export["name"])
        self.assertEqual(model_export.description, node_export["description"])

    def compare_place_export_edges(self, place_exports, edges):
        for i, placeexport in enumerate(place_exports):
            significance_display = PlaceExport.SIGNIFICANCE[placeexport.significance][1]
            self.assertEqual(significance_display, edges[i]["significance"])
            self.compare_exports(placeexport.export, edges[i]["node"])

    def compare_races(self, model_race, node_race):
        self.assertEqual(str(model_race.id), from_global_id(node_race["id"])[1])
        self.assertEqual(model_race.name, node_race["name"])

    def compare_place_race_edges(self, place_races, edges):
        for i, placerace in enumerate(place_races):
            self.assertEqual(placerace.percent, edges[i]["percent"])
            self.assertEqual(placerace.notes, edges[i]["notes"])
            self.compare_races(placerace.race, edges[i]["node"])

    def compare_places(
        self,
        model_place,
        node_place,
        compare_associations=False,
        compare_exports=False,
        compare_races=False,
        compare_parents_to_depth=0,
        compare_children_to_depth=0,
    ):
        self.assertEqual(str(model_place.id), from_global_id(node_place["id"])[1])
        self.assertEqual(model_place.name, node_place["name"])
        self.assertEqual(model_place.description, node_place["description"])
        self.assertEqual(model_place.image_ids, node_place["imageIds"])
        self.assertEqual(model_place.thumbnail_id, node_place["thumbnailId"])
        self.assertEqual(model_place.place_type.upper(), node_place["placeType"])
        self.assertEqual(model_place.population, node_place["population"])

        if compare_parents_to_depth > 0 and model_place.parent:
            self.compare_places(
                model_place.parent,
                node_place["parent"],
                compare_parents_to_depth=compare_parents_to_depth - 1,
            )

        if compare_children_to_depth > 0 and model_place.children.count() > 0:
            for i, child in enumerate(model_place.children.all()):
                self.compare_places(
                    child,
                    node_place["children"]["edges"][i]["node"],
                    compare_children_to_depth=compare_children_to_depth - 1,
                )

        if compare_associations:
            place_associations = model_place.placeassociation_set.all()
            associations_edges = node_place["associations"]["edges"]
            self.compare_place_association_edges(place_associations, associations_edges)

        if compare_exports:
            place_exports = model_place.placeexport_set.all()
            exports_edges = node_place["exports"]["edges"]
            self.compare_place_export_edges(place_exports, exports_edges)

        if compare_races:
            place_races = model_place.placerace_set.all()
            races_edges = node_place["commonRaces"]["edges"]
            self.compare_place_race_edges(place_races, races_edges)


class PlaceQueryTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_basic_place_list_query(self):
        places = PlaceFactory.create_batch(2)

        response = self.client.execute(
            """
            query {
                places {
                    edges {
                        node {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
                            created
                            updated
                            placeType
                            population
                        }
                    }
                }
            }
            """
        )
        self.assertIsNone(response.errors)
        res_places = response.data["places"]["edges"]

        self.assertEqual(len(res_places), 2)
        for i, place in enumerate(places):
            equivalent_place = res_places[i]["node"]
            self.assertEqual(str(place.id), from_global_id(equivalent_place["id"])[1])
            self.assertEqual(place.name, equivalent_place["name"])
            self.assertEqual(place.description, equivalent_place["description"])
            self.assertEqual(place.image_ids, equivalent_place["imageIds"])
            self.assertEqual(place.thumbnail_id, equivalent_place["thumbnailId"])
            self.assertEqual(place.place_type.upper(), equivalent_place["placeType"])
            self.assertEqual(place.population, equivalent_place["population"])

    def test_place_list_query(self):
        place_great_grandparent = PlaceFactory()
        place_grandparent = PlaceFactory(parent=place_great_grandparent)
        place_parent = PlaceFactory(parent=place_grandparent)
        place = PlaceFactory(parent=place_parent)
        places = Place.objects.all()

        response = self.client.execute(
            """
            query {
                places {
                    edges {
                        node {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
                            created
                            updated
                            placeType
                            population
                            parent {
                                id
                                name
                                description
                                imageIds
                                thumbnailId
                                created
                                updated
                                placeType
                                population
                                parent {
                                    id
                                    name
                                    description
                                    imageIds
                                    thumbnailId
                                    created
                                    updated
                                    placeType
                                    population
                                }
                            }
                        }
                    }
                }
            }
            """
        )
        self.assertIsNone(response.errors)

        self.assertEqual(len(response.data["places"]["edges"]), places.count())
        for i, place in enumerate(places):
            equivalent_place = response.data["places"]["edges"][i]["node"]
            self.compare_places(place, equivalent_place, compare_parents_to_depth=2)

    def test_basic_place_detail_query(self):
        place = PlaceFactory()

        response = self.client.execute(
            """
            query {
                place(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    created
                    updated
                    placeType
                    population
                }
            }
            """
            % to_global_id("PlaceNode", place.id)
        )
        self.assertIsNone(response.errors)

        res_place = response.data["place"]

        self.compare_places(place, res_place)

    def test_place_detail_query_with_parents(self):
        place_grandparent = PlaceFactory(name="place_grandparent")
        place_parent = PlaceFactory(parent=place_grandparent, name="place_parent")
        place = PlaceFactory(parent=place_parent, name="place")
        PlaceFactory(parent=place, name="place_child1")
        PlaceFactory(parent=place, name="place_child2")

        response = self.client.execute(
            """
            query {
                place(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    created
                    updated
                    placeType
                    population
                    parent {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        parent {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
                            created
                            updated
                            placeType
                            population
                        }
                    }
                    children {
                        edges {
                            node {
                                id
                                name
                                description
                                imageIds
                                thumbnailId
                                created
                                updated
                                placeType
                                population
                            }
                        }
                    }
                }
            }
            """
            % to_global_id("PlaceNode", place.id)
        )
        self.assertIsNone(response.errors)

        res_place = response.data["place"]

        self.assertEqual(res_place["parent"]["parent"]["name"], place_grandparent.name)
        self.assertEqual(len(res_place["children"]["edges"]), 2)

        self.compare_places(
            place,
            res_place,
            compare_parents_to_depth=2,
            compare_children_to_depth=1,
        )

    def test_place_detail_query_with_m2m_associations(self):
        place1 = PlaceFactory()
        place2 = PlaceFactory()
        association1 = AssociationFactory()
        association2 = AssociationFactory()
        PlaceAssociationFactory(place=place1, association=association1)
        PlaceAssociationFactory(place=place1, association=association2)
        PlaceAssociationFactory(place=place2, association=association1)
        PlaceAssociationFactory(place=place2, association=association2)

        response = self.client.execute(
            """
            query {
                place(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    created
                    updated
                    placeType
                    population
                    associations {
                        edges {
                            notes
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
            % to_global_id("PlaceNode", place1.id)
        )
        self.assertIsNone(response.errors)

        res_place = response.data["place"]

        self.assertEqual(len(res_place["associations"]["edges"]), 2)
        self.compare_places(place1, res_place, compare_associations=True)

    def test_place_detail_query_with_m2m_exports(self):
        place1 = PlaceFactory()
        place2 = PlaceFactory()
        export1 = ExportFactory()
        export2 = ExportFactory()
        PlaceExportFactory(place=place1, export=export1)
        PlaceExportFactory(place=place1, export=export2)
        PlaceExportFactory(place=place2, export=export1)
        PlaceExportFactory(place=place2, export=export2)

        response = self.client.execute(
            """
            query {
                place(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    created
                    updated
                    placeType
                    population
                    exports {
                        edges {
                            significance
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
            % to_global_id("PlaceNode", place1.id)
        )
        self.assertIsNone(response.errors)

        res_place = response.data["place"]

        self.assertEqual(len(res_place["exports"]["edges"]), 2)
        self.compare_places(place1, res_place, compare_exports=True)

    def test_place_detail_query_with_m2m_races(self):
        place1 = PlaceFactory()
        place2 = PlaceFactory()
        race1 = RaceFactory()
        race2 = RaceFactory()
        PlaceRaceFactory(place=place1, race=race1)
        PlaceRaceFactory(place=place1, race=race2)
        PlaceRaceFactory(place=place2, race=race1)
        PlaceRaceFactory(place=place2, race=race2)

        response = self.client.execute(
            """
            query {
                place(id: "%s") {
                    id
                    name
                    description
                    imageIds
                    thumbnailId
                    created
                    updated
                    placeType
                    population
                    commonRaces {
                        edges {
                            percent
                            notes
                            node {
                                id
                                name
                            }
                        }
                    }
                }
            }
            """
            % to_global_id("PlaceNode", place1.id)
        )
        self.assertIsNone(response.errors)

        res_place = response.data["place"]

        self.assertEqual(len(res_place["commonRaces"]["edges"]), 2)
        self.compare_places(place1, res_place, compare_races=True)


class PlaceMutationTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_basic_place_create_mutation(self):
        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_place = response.data["placeCreate"]["place"]

        self.assertEqual(res_place["name"], "Test Place Name")
        self.assertEqual(res_place["description"], "Test Place Description")
        self.assertEqual(res_place["imageIds"], ["test-image-id-1", "test-image-id-2"])
        self.assertEqual(res_place["thumbnailId"], "test-thumbnail-id")

        created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])
        self.assertEqual(created_place.name, "Test Place Name")
        self.assertEqual(created_place.description, "Test Place Description")
        self.assertEqual(
            created_place.image_ids, ["test-image-id-1", "test-image-id-2"]
        )
        self.assertEqual(created_place.thumbnail_id, "test-thumbnail-id")

        self.compare_places(created_place, res_place)

    def test_place_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                placeCreate(input: {
                    description: "Test Place Description"
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        created
                        updated
                        placeType
                        population
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_place_create_with_parent(self):
        parent = PlaceFactory()
        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                    parent: {
                        id: "%s"
                    }
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        parent {
                            id
                            name
                            description
                            imageIds
                            thumbnailId
                            created
                            updated
                            placeType
                            population
                        }
                    }
                }
            }
        """ % to_global_id(
            "PlaceNode", parent.id
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_place = response.data["placeCreate"]["place"]

        created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

        self.compare_places(created_place, res_place, compare_parents_to_depth=1)

    def test_place_create_with_adding_existing_exports(self):
        export1 = ExportFactory()
        export2 = ExportFactory()

        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                    exports: [{
                        significance: 0
                        export: "%s"
                    }, {
                        significance: 1
                        export: "%s"
                    }]
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        exports {
                            edges {
                                significance
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
            to_global_id("ExportNode", export1.id),
            to_global_id("ExportNode", export2.id),
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_place = response.data["placeCreate"]["place"]

        created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

        self.assertEqual(len(created_place.exports.all()), 2)
        self.compare_places(created_place, res_place, compare_exports=True)

    def test_place_create_fails_with_nonexisting_export_ids(self):
        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                    exports: [{
                        significance: 0
                        export: "%s"
                    }, {
                        significance: 1
                        export: "%s"
                    }]
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        exports {
                            edges {
                                significance
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
            to_global_id("ExportNode", 23456),
            to_global_id("ExportNode", 12345),
        )

        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

        with self.assertRaises(Place.DoesNotExist):
            Place.objects.get(name="Test Place Name")

    def test_place_create_with_adding_existing_associations(self):
        association1 = AssociationFactory()
        association2 = AssociationFactory()

        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                    associations: [{
                        notes: "Test Notes 1"
                        association: "%s"
                    }, {
                        notes: "Test Notes 2"
                        association: "%s"
                    }]
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        associations {
                            edges {
                                notes
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
            to_global_id("AssociationNode", association1.id),
            to_global_id("AssociationNode", association2.id),
        )

        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_place = response.data["placeCreate"]["place"]

        created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

        self.assertEqual(len(created_place.associations.all()), 2)
        self.compare_places(created_place, res_place, compare_associations=True)

    def test_place_create_fails_with_nonexisting_association_ids(self):
        query = """
            mutation {
                placeCreate(input: {
                    name: "Test Place Name"
                    description: "Test Place Description"
                    imageIds: ["test-image-id-1", "test-image-id-2"]
                    thumbnailId: "test-thumbnail-id"
                    placeType: "TOWN"
                    population: 100
                    associations: [{
                        significance: 0
                        association: "%s"
                    }, {
                        significance: 1
                        association: "%s"
                    }]
                }) {
                    ok
                    errors
                    place {
                        id
                        name
                        description
                        imageIds
                        thumbnailId
                        created
                        updated
                        placeType
                        population
                        associations {
                            edges {
                                notes
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
            to_global_id("AssociationNode", 23456),
            to_global_id("AssociationNode", 12345),
        )

        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

        with self.assertRaises(Place.DoesNotExist):
            Place.objects.get(name="Test Place Name")

        # ASSOCIATIONS AND RACES REMAIN

        # def test_association_create_with_common_races(self):
        #     query = """
        #         mutation {
        #             placeCreate(input: {
        #                 name: "Test Place Name"
        #                 description: "Test Place Description"
        #                 placeType: "TOWN"
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
        #                 place {
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
        #         }
        #     """

        #     response = self.client.execute(query)
        #     self.assertIsNone(response.errors)

        #
        #     res_place = response.data["placeCreate"]["place"]

        #     created_place = Place.objects.get(pk=from_global_id(res_place["id"])[1])

        #     self.assertEqual(len(created_place.exports.all()), 2)
        #     self.compare_places(created_place, res_place, compare_exports=True)

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
