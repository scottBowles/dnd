import json
from graphene_django.utils.testing import GraphQLTestCase
from ..models import PlaceExport
from graphql_relay import from_global_id, to_global_id
from .factories import ExportFactory, PlaceFactory, PlaceExportFactory

"""
PlaceExport Tests
Tests for the pivot table between PlaceExport and Place
"""


class PlaceExportTests(GraphQLTestCase):
    def setUp(self):
        super().setUp()
        self.place = PlaceFactory()
        self.export = ExportFactory()
        self.significance = PlaceExport.SIGNIFICANCE[0]

    def test_placeexport_create_mutation(self):
        query = """
            mutation {
                placeExportCreate(input: {
                    place: "%s"
                    export: "%s"
                    significance: %s
                }) {
                    ok
                    errors
                    placeExport {
                        id
                        place {
                            id
                            name
                            description
                        }
                        export {
                            id
                            name
                            description
                        }
                        significance
                    }
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            to_global_id("ExportNode", self.export.pk),
            self.significance[0],
        )

        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_placeExport = result["data"]["placeExportCreate"]["placeExport"]

        self.assertEqual(
            res_placeExport["place"]["id"], to_global_id("PlaceNode", self.place.id)
        )
        self.assertEqual(
            res_placeExport["export"]["id"], to_global_id("ExportNode", self.export.id)
        )
        self.assertEqual(res_placeExport["significance"], self.significance[1])

        created_placeExport = PlaceExport.objects.get(
            pk=from_global_id(res_placeExport["id"])[1]
        )
        self.assertEqual(created_placeExport.place.id, self.place.id)
        self.assertEqual(created_placeExport.export.id, self.export.id)
        self.assertEqual(created_placeExport.significance, self.significance[0])

    def test_placeExport_create_bad_input(self):
        query = """
            mutation {
                placeExportCreate(input: {
                    export: "%s"
                    significance: %s
                }) {
                    ok
                    errors
                    placeExport {
                        place
                        export
                        significance
                    }
                }
            }
        """ % (
            to_global_id("ExportNode", self.export.pk),
            self.significance[0],
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_placeExport_update_mutation(self):
        PlaceExportFactory(
            place=self.place, export=self.export, significance=self.significance[0]
        )
        query = """
            mutation {
                placeExportUpdate(input: {
                    place: "%s"
                    export: "%s"
                    significance: %s
                }) {
                    placeExport {
                        id
                        place {
                            id
                            name
                            description
                        }
                        export {
                            id
                            name
                            description
                        }
                        significance
                    }
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            to_global_id("ExportNode", self.export.pk),
            PlaceExport.SIGNIFICANCE[1][0],
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_placeExport = result["data"]["placeExportUpdate"]["placeExport"]

        self.assertEqual(
            res_placeExport["place"]["id"], to_global_id("PlaceNode", self.place.id)
        )
        self.assertEqual(res_placeExport["place"]["name"], self.place.name)
        self.assertEqual(
            res_placeExport["export"]["id"], to_global_id("ExportNode", self.export.id)
        )
        self.assertEqual(res_placeExport["export"]["name"], self.export.name)
        self.assertEqual(
            res_placeExport["significance"], PlaceExport.SIGNIFICANCE[1][1]
        )

        updated_placeExport = PlaceExport.objects.get(
            pk=from_global_id(res_placeExport["id"])[1]
        )
        self.assertEqual(updated_placeExport.place.pk, self.place.pk)
        self.assertEqual(updated_placeExport.export.pk, self.export.pk)
        self.assertEqual(
            updated_placeExport.significance, PlaceExport.SIGNIFICANCE[1][0]
        )

    """
    NEXT UP:
    WE PROBABLY DON'T WANT TO DEAL WITH PlaceExport IDS. SHOULD JUST NEED PLACE AND EXPORT. FIGURE OUT WHAT THAT WILL LOOK LIKE.
    SEE WHAT OF THE BELOW IS NEEDED
    SHOULD THE ABOVE BE PATCH? BOTH WORK THE SAME? PROBABLY NEED ONLY EITHER ID OR PLACE/EXPORT DEPENDING ON HOW WE HANDLE THAT
    """

    def test_placeExport_update_bad_input_no_export(self):
        PlaceExportFactory()
        query = """
            mutation {
                placeExportUpdate(input: {
                    place: "%s"
                    significance: "%s"
                }) {
                    placeExport {
                        id
                        name
                        description
                    }
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            self.significance[0],
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_placeExport_patch_mutation(self):
        PlaceExportFactory(
            place=self.place, export=self.export, significance=self.significance[0]
        )
        query = """
            mutation {
                placeExportPatch(input: {
                    place: "%s"
                    export: "%s"
                    significance: %s
                }) {
                    placeExport {
                        id
                        place {
                            id
                            name
                            description
                        }
                        export {
                            id
                            name
                            description
                        }
                        significance
                    }
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            to_global_id("ExportNode", self.export.pk),
            PlaceExport.SIGNIFICANCE[1][0],
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_placeExport = result["data"]["placeExportPatch"]["placeExport"]

        self.assertEqual(
            res_placeExport["place"]["id"], to_global_id("PlaceNode", self.place.id)
        )
        self.assertEqual(res_placeExport["place"]["name"], self.place.name)
        self.assertEqual(
            res_placeExport["export"]["id"], to_global_id("ExportNode", self.export.id)
        )
        self.assertEqual(res_placeExport["export"]["name"], self.export.name)
        self.assertEqual(
            res_placeExport["significance"], PlaceExport.SIGNIFICANCE[1][1]
        )

        updated_placeExport = PlaceExport.objects.get(
            pk=from_global_id(res_placeExport["id"])[1]
        )
        self.assertEqual(updated_placeExport.place.pk, self.place.pk)
        self.assertEqual(updated_placeExport.export.pk, self.export.pk)
        self.assertEqual(
            updated_placeExport.significance, PlaceExport.SIGNIFICANCE[1][0]
        )

    """
    NEXT UP:
    WE PROBABLY DON'T WANT TO DEAL WITH PlaceExport IDS. SHOULD JUST NEED PLACE AND EXPORT. FIGURE OUT WHAT THAT WILL LOOK LIKE.
    SEE WHAT OF THE BELOW IS NEEDED
    SHOULD THE ABOVE BE PATCH? BOTH WORK THE SAME? PROBABLY NEED ONLY EITHER ID OR PLACE/EXPORT DEPENDING ON HOW WE HANDLE THAT
    """

    def test_placeExport_patch_bad_input_no_export(self):
        PlaceExportFactory()
        query = """
            mutation {
                placeExportPatch(input: {
                    place: "%s"
                    description: "%s"
                }) {
                    placeExport {
                        place {
                            id
                        }
                    }
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            self.significance[0],
        )
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_placeExport_delete(self):
        placeExport = PlaceExportFactory(place=self.place, export=self.export)
        query = """
            mutation {
                placeExportDelete(input: {
                    place: "%s"
                    export: "%s"
                }) {
                    ok
                }
            }
        """ % (
            to_global_id("PlaceNode", self.place.pk),
            to_global_id("ExportNode", self.export.pk),
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        self.assertTrue(result["data"]["placeExportDelete"]["ok"])

        with self.assertRaises(PlaceExport.DoesNotExist):
            PlaceExport.objects.get(pk=placeExport.id)
