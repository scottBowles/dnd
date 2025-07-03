import strawberry
from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth.transport import requests
from google.oauth2 import id_token
from gqlauth.jwt.types_ import ObtainJSONWebTokenType

user_model = get_user_model()


@strawberry.type
class LoginMutation:
    @strawberry.mutation
    def google_login(self, google_token: str) -> ObtainJSONWebTokenType:
        print("google_login start")
        # take in the google_token
        # verify the google_token
        # if the google_token is invalid, an error is thrown
        # try to find the user in the database
        # if the user is not in the database, create a new user
        # return a JWT token for the user
        idinfo = id_token.verify_oauth2_token(
            google_token, requests.Request(), settings.GOOGLE_SSO_CLIENT_ID
        )
        print("email: ", idinfo["email"])
        user = user_model.objects.filter(email=idinfo["email"]).first()
        if user:
            print("user found")
            print("user: ", user)

        if not user:
            print("user not found")
            username = idinfo["email"].split("@")[0].split("+")[0]
            user = user_model.objects.create_user(
                email=idinfo["email"],
                username=username,
                first_name=idinfo["given_name"],
                last_name=idinfo["family_name"],
                # password="",  # set unusable password?
            )
            print("user created")
            print("user: ", user)

        # same return as gqlauth's token_auth mutation
        return ObtainJSONWebTokenType.from_user(user)
