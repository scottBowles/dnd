# import json
# from graphql_jwt.testcases import JSONWebTokenTestCase
# from ..models import Export
# from graphql_relay import from_global_id, to_global_id
# from .factories import ExportFactory


# class ExportTests(JSONWebTokenTestCase):
#     def test_export_list_query(self):
#         factory1 = ExportFactory()
#         factory2 = ExportFactory()
#         query = """
#             query {
#                 exports {
#                     edges {
#                         node {
#                             id
#                             name
#                             description
#                         }
#                     }
#                 }
#             }
#         """
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         res_1 = response.data["exports"]["edges"][0]["node"]
#         res_2 = response.data["exports"]["edges"][1]["node"]

#         # Ensure exactly two results exist, have expected values, and are in the expected order
#         self.assertEqual(from_global_id(res_1["id"])[1], str(factory1.id))
#         self.assertEqual(res_1["name"], factory1.name)
#         self.assertEqual(res_1["description"], factory1.description)
#         self.assertEqual(from_global_id(res_2["id"])[1], str(factory2.id))
#         self.assertEqual(res_2["name"], factory2.name)
#         self.assertEqual(res_2["description"], factory2.description)
#         with self.assertRaises(IndexError):
#             response.data["exports"]["edges"][2]

#     def test_bad_export_list_query(self):
#         ExportFactory()
#         query = """
#             query {
#                 exports {
#                     edges {
#                         node {
#                             id
#                             name
#                             description
#                             not_a_field
#                         }
#                     }
#                 }
#             }
#         """
#         response = self.client.execute(query)
#         self.assertIsNotNone(response.errors)

#     def test_export_retrieve_query(self):
#         export = ExportFactory()
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             query {
#                 export(id: "%s") {
#                     id
#                     name
#                     description
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         res_export = response.data["export"]

#         self.assertEqual(res_export["name"], export.name)
#         self.assertEqual(res_export["description"], export.description)

#     def test_export_create_mutation(self):
#         query = """
#             mutation {
#                 exportCreate(input: {
#                     name: "Test Export Name"
#                     description: "Test Export Description"
#                 }) {
#                     ok
#                     errors
#                     export {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                     }
#                 }
#             }
#         """
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         res_export = response.data["exportCreate"]["export"]

#         self.assertEqual(res_export["name"], "Test Export Name")
#         self.assertEqual(res_export["description"], "Test Export Description")

#         created_export = Export.objects.get(pk=from_global_id(res_export["id"])[1])
#         self.assertEqual(created_export.name, "Test Export Name")
#         self.assertEqual(created_export.description, "Test Export Description")

#     def test_export_create_bad_input(self):  # (no `name` value provided)
#         query = """
#             mutation {
#                 exportCreate(input: {
#                     description: "Test Export Description"
#                 }) {
#                     ok
#                     errors
#                     export {
#                         id
#                         name
#                         description
#                         created
#                         updated
#                     }
#                 }
#             }
#         """
#         response = self.client.execute(query)
#         self.assertIsNotNone(response.errors)

#     def test_export_update_mutation(self):
#         export = ExportFactory(
#             name="Not Test Export Name", description="Not Test Export Description"
#         )
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             mutation {
#                 exportUpdate(input: {
#                     id: "%s"
#                     name: "Test Export Name"
#                     description: "Test Export Description"
#                 }) {
#                     export {
#                         id
#                         name
#                         description
#                     }
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         res_export = response.data["exportUpdate"]["export"]

#         self.assertEqual(res_export["name"], "Test Export Name")
#         self.assertEqual(res_export["description"], "Test Export Description")

#         updated_export = Export.objects.get(pk=from_global_id(res_export["id"])[1])
#         self.assertEqual(updated_export.name, "Test Export Name")
#         self.assertEqual(updated_export.description, "Test Export Description")

#     def test_export_update_bad_input_no_id(self):
#         ExportFactory()
#         query = """
#             mutation {
#                 exportUpdate(input: {
#                     place: "%s"
#                     export: "%s"
#                     significance: "%s"
#                 }) {
#                     export {
#                         id
#                         name
#                         description
#                     }
#                 }
#             }
#         """
#         response = self.client.execute(query)
#         self.assertIsNotNone(response.errors)

#     def test_export_update_bad_input_no_name(self):
#         export = ExportFactory()
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             mutation {
#                 exportUpdate(input: {
#                     id: "%s"
#                     description: "Test Export Description"
#                 }) {
#                     export {
#                         id
#                         name
#                         description
#                     }
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNotNone(response.errors)

#     def test_export_patch(self):
#         export = ExportFactory(
#             name="Not Test Export Name", description="Test Export Description"
#         )
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             mutation {
#                 exportPatch(input: {
#                     id: "%s"
#                     name: "Test Export Name"
#                 }) {
#                     export {
#                         id
#                         name
#                         description
#                     }
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         res_export = response.data["exportPatch"]["export"]
#         self.assertEqual(res_export["name"], "Test Export Name")
#         self.assertEqual(res_export["description"], "Test Export Description")

#     def test_export_patch_null_name(self):
#         export = ExportFactory(
#             name="Not Test Export Name", description="Test Export Description"
#         )
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             mutation {
#                 exportPatch(input: {
#                     id: "%s"
#                     name: null
#                 }) {
#                     export {
#                         id
#                         name
#                         description
#                     }
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNotNone(response.errors)

#     def test_export_delete(self):
#         export = ExportFactory()
#         export_global_id = to_global_id("ExportNode", export.id)
#         query = (
#             """
#             mutation {
#                 exportDelete(input: {
#                     id: "%s"
#                 }) {
#                     ok
#                 }
#             }
#         """
#             % export_global_id
#         )
#         response = self.client.execute(query)
#         self.assertIsNone(response.errors)

#
#         self.assertTrue(response.data["exportDelete"]["ok"])

#         with self.assertRaises(Export.DoesNotExist):
#             Export.objects.get(pk=export.id)
