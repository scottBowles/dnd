import json
import factory
from graphene_django.utils.testing import GraphQLTestCase
from .models import User
from graphql_relay import from_global_id, to_global_id


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "user{}".format(n))
    email = factory.Sequence(lambda n: "email{}".format(n))
    password = factory.PostGenerationMethodCall("set_password", "password")
    isDM = factory.Faker("pybool")


class UserTests(GraphQLTestCase):
    def test_user_list_query(self):
        factory1 = UserFactory()
        factory2 = UserFactory()
        query = """
            query {
                users {
                    edges {
                        node {
                            id
                            username
                            email
                            isDM
                            firstName
                            lastName
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_1 = result["data"]["users"]["edges"][0]["node"]
        res_2 = result["data"]["users"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.assertEqual(from_global_id(res_1["id"])[1], str(factory1.id))
        self.assertEqual(res_1["username"], factory1.username)
        self.assertEqual(res_1["email"], factory1.email)
        self.assertEqual(res_1["isDM"], factory1.isDM)
        self.assertEqual(res_1["firstName"], factory1.first_name)
        self.assertEqual(res_1["lastName"], factory1.last_name)
        self.assertEqual(from_global_id(res_2["id"])[1], str(factory2.id))
        self.assertEqual(res_2["username"], factory2.username)
        self.assertEqual(res_2["email"], factory2.email)
        self.assertEqual(res_2["isDM"], factory2.isDM)
        self.assertEqual(res_2["firstName"], factory2.first_name)
        self.assertEqual(res_2["lastName"], factory2.last_name)
        with self.assertRaises(IndexError):
            result["data"]["users"]["edges"][2]

    def test_bad_user_list_query(self):
        UserFactory()
        query = """
            query {
                users {
                    edges {
                        node {
                            id
                            username
                            email
                            isDM
                            firstName
                            notAField
                        }
                    }
                }
            }
        """
        response = self.query(query)
        self.assertResponseHasErrors(response)

    def test_user_detail_query(self):
        user = UserFactory()
        user_global_id = to_global_id("UserNode", user.id)
        query = (
            """
            query {
                user(id: "%s") {
                    id
                    username
                    email
                    isDM
                    firstName
                    lastName
                }
            }
        """
            % user_global_id
        )
        response = self.query(query)
        self.assertResponseNoErrors(response)

        result = json.loads(response.content)
        res_user = result["data"]["user"]

        self.assertEqual(res_user["username"], user.username)
        self.assertEqual(res_user["email"], user.email)
        self.assertEqual(res_user["isDM"], user.isDM)
        self.assertEqual(res_user["firstName"], user.first_name)
        self.assertEqual(res_user["lastName"], user.last_name)
