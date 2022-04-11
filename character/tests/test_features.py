import json
from graphql_jwt.testcases import JSONWebTokenTestCase
from ..models import Feature
from graphql_relay import from_global_id, to_global_id
from .factories import FeatureFactory
from .utils import CompareMixin
from django.contrib.auth import get_user_model


class FeatureTests(CompareMixin, JSONWebTokenTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="test")
        self.client.authenticate(self.user)

    def test_feature_list_query(self):
        factory1 = FeatureFactory()
        factory2 = FeatureFactory()
        query = """
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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_1 = response.data["features"]["edges"][0]["node"]
        res_2 = response.data["features"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.compare_features(factory1, res_1)
        self.compare_features(factory2, res_2)
        with self.assertRaises(IndexError):
            response.data["features"]["edges"][2]

    def test_bad_feature_list_query(self):
        FeatureFactory()
        query = """
            query {
                features {
                    edges {
                        node {
                            id
                            name
                            description
                            not_a_field
                        }
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_feature_detail_query(self):
        feature = FeatureFactory()
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            query {
                feature(id: "%s") {
                    id
                    name
                    description
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_feature = response.data["feature"]

        self.compare_features(feature, res_feature)

    def test_feature_create_mutation(self):
        query = """
            mutation {
                featureCreate(input: {
                    name: "Test Feature Name"
                    description: "Test Feature Description"
                }) {
                    ok
                    errors
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_feature = response.data["featureCreate"]["feature"]

        self.assertEqual(res_feature["name"], "Test Feature Name")
        self.assertEqual(res_feature["description"], "Test Feature Description")

        created_feature = Feature.objects.get(pk=from_global_id(res_feature["id"])[1])
        self.assertEqual(created_feature.name, "Test Feature Name")
        self.assertEqual(created_feature.description, "Test Feature Description")

    def test_feature_create_bad_input(self):  # (no `name` value provided)
        query = """
            mutation {
                featureCreate(input: {
                    description: "Test Feature Description"
                }) {
                    ok
                    errors
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_feature_update_mutation(self):
        feature = FeatureFactory(
            name="Not Test Feature Name", description="Not Test Feature Description"
        )
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            mutation {
                featureUpdate(input: {
                    id: "%s"
                    name: "Test Feature Name"
                    description: "Test Feature Description"
                }) {
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_feature = response.data["featureUpdate"]["feature"]

        self.assertEqual(res_feature["name"], "Test Feature Name")
        self.assertEqual(res_feature["description"], "Test Feature Description")

        updated_feature = Feature.objects.get(pk=from_global_id(res_feature["id"])[1])
        self.assertEqual(updated_feature.name, "Test Feature Name")
        self.assertEqual(updated_feature.description, "Test Feature Description")
        self.compare_features(updated_feature, res_feature)

    def test_feature_update_bad_input_no_id(self):
        FeatureFactory()
        query = """
            mutation {
                featureUpdate(input: {
                    name: "Test Feature Name"
                    description: "Test Feature Description"
                }) {
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_feature_update_bad_input_no_name(self):
        feature = FeatureFactory()
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            mutation {
                featureUpdate(input: {
                    id: "%s"
                    description: "Test Feature Description"
                }) {
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_feature_patch(self):
        feature = FeatureFactory(
            name="Test Feature Name", description="Not Test Feature Description"
        )
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            mutation {
                featurePatch(input: {
                    id: "%s"
                    description: "Test Feature Description"
                }) {
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_feature = response.data["featurePatch"]["feature"]
        self.assertEqual(res_feature["name"], "Test Feature Name")
        self.assertEqual(res_feature["description"], "Test Feature Description")
        updated_feature = Feature.objects.get(pk=feature.pk)
        self.compare_features(updated_feature, res_feature)

    def test_feature_patch_null_name(self):
        feature = FeatureFactory(
            name="Not Test Feature Name", description="Test Feature Description"
        )
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            mutation {
                featurePatch(input: {
                    id: "%s"
                    name: null
                }) {
                    feature {
                        id
                        name
                        description
                    }
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

    def test_feature_delete(self):
        feature = FeatureFactory()
        feature_global_id = to_global_id("FeatureNode", feature.id)
        query = (
            """
            mutation {
                featureDelete(input: {
                    id: "%s"
                }) {
                    ok
                }
            }
        """
            % feature_global_id
        )
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        self.assertTrue(response.data["featureDelete"]["ok"])

        with self.assertRaises(Feature.DoesNotExist):
            Feature.objects.get(pk=feature.id)
