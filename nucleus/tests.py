import json
import factory
from graphql_jwt.testcases import JSONWebTokenTestCase
from .models import User
from graphql_relay import from_global_id, to_global_id
from django.contrib.auth import get_user_model


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "user{}".format(n))
    email = factory.Sequence(lambda n: "email{}".format(n))
    password = factory.PostGenerationMethodCall("set_password", "password")
    isDM = factory.Faker("pybool")


class UserTests(JSONWebTokenTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.authenticate(self.user)

    def test_user_list_query(self):
        first_user = self.user
        second_user = UserFactory()
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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_1 = response.data["users"]["edges"][0]["node"]
        res_2 = response.data["users"]["edges"][1]["node"]

        # Ensure exactly two results exist, have expected values, and are in the expected order
        self.assertEqual(from_global_id(res_1["id"])[1], str(first_user.id))
        self.assertEqual(res_1["username"], first_user.username)
        self.assertEqual(res_1["email"], first_user.email)
        self.assertEqual(res_1["isDM"], first_user.isDM)
        self.assertEqual(res_1["firstName"], first_user.first_name)
        self.assertEqual(res_1["lastName"], first_user.last_name)
        self.assertEqual(from_global_id(res_2["id"])[1], str(second_user.id))
        self.assertEqual(res_2["username"], second_user.username)
        self.assertEqual(res_2["email"], second_user.email)
        self.assertEqual(res_2["isDM"], second_user.isDM)
        self.assertEqual(res_2["firstName"], second_user.first_name)
        self.assertEqual(res_2["lastName"], second_user.last_name)
        with self.assertRaises(IndexError):
            response.data["users"]["edges"][2]

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
        response = self.client.execute(query)
        self.assertIsNotNone(response.errors)

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
        response = self.client.execute(query)
        self.assertIsNone(response.errors)

        res_user = response.data["user"]

        self.assertEqual(res_user["username"], user.username)
        self.assertEqual(res_user["email"], user.email)
        self.assertEqual(res_user["isDM"], user.isDM)
        self.assertEqual(res_user["firstName"], user.first_name)
        self.assertEqual(res_user["lastName"], user.last_name)
