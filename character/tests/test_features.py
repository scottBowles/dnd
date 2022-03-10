import random
import json
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay import to_global_id
from .factories import FeatureFactory
from .utils import CompareMixin


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
