import json

from django.contrib.auth import get_user_model
from django.utils import timezone
from gqlauth.models import RefreshToken

User = get_user_model()


class PrintRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # print("request.path")
        # print(request.path)
        # print("request.method")
        # print(request.method)
        # print("request.body")
        # print(request.body)
        # print("request.META")
        # print("request.META")
        # print("request.get_host()")
        # print(request.get_host())
        # print("request.headers")
        # print(request.headers)
        # print("request.META.get('HTTP_ORIGIN')")
        # print(request.META.get("HTTP_ORIGIN"))
        response = self.get_response(request)
        # print("response.content")
        # print(response.content)
        # print("response.headers")
        # print(response.headers)
        return response


class TokenRefreshActivityMiddleware:
    """
    Middleware that updates user activity when refresh token mutations are called.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        refresh_token = self._request_token_if_is_token_refresh(request)

        # Process the request
        response = self.get_response(request)

        if refresh_token and response.status_code == 200:
            user = self._get_user_from_refresh_token(refresh_token)
            if user:
                User.objects.filter(pk=user.pk).update(last_activity=timezone.now())

        return response

    def _request_token_if_is_token_refresh(self, request):
        """
        If this is a refresh token mutation, return the token from the request.
        Otherwise return None.
        """
        if (
            request.path.startswith("/graphql")
            and request.method == "POST"
            and request.content_type == "application/json"
        ):
            try:
                body = json.loads(request.body.decode("utf-8"))
                query = body.get("query", "")
                variables = body.get("variables", {})

                # Check if this is a refresh token mutation and extract the token
                if ("refreshToken" in query or "refresh_token" in query) and variables:
                    # Extract refresh token from variables
                    return variables.get("refreshToken") or variables.get(
                        "refresh_token"
                    )

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                pass

        return None

    def _get_user_from_refresh_token(self, refresh_token):
        """
        Given a refresh token string, return the associated user or None.
        """
        try:
            token_obj = (
                RefreshToken.objects.select_related("user")
                .filter(
                    token=refresh_token,
                    revoked__isnull=True,  # Only active (non-revoked) tokens
                )
                .first()
            )
            if token_obj:
                return token_obj.user
        except Exception:
            pass
        return None
