import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry.types import Info

from strawberry_django.relay import DjangoListConnection

from .. import models
from ..models import ActivityType
from ..signals import record_activity


@strawberry_django.type(models.User)
class User(relay.Node):
    isDM: auto
    last_activity: auto
    username: auto
    first_name: auto
    last_name: auto
    email: auto
    is_staff: auto
    is_active: auto
    date_joined: auto
    last_login: auto


# @strawberry.type
# class UserQuery:
#     users: DjangoListConnection[User] = strawberry_django.connection()


@strawberry_django.input(models.User)
class UserInput:
    username: auto
    password: auto
    first_name: auto
    last_name: auto
    email: auto


@strawberry_django.partial(models.User)
class UserInputPartial(strawberry_django.NodeInput):
    username: auto
    password: auto
    first_name: auto
    last_name: auto
    email: auto


@strawberry.type
class UserMutation:
    @strawberry.mutation
    def record_page_view(self, info: Info, path: str) -> bool:
        """Record a page view. Works for both authenticated and anonymous users."""
        request_user = info.context.request.user
        user = request_user if request_user.is_authenticated else None
        record_activity(user=user, activity_type=ActivityType.PAGE_VIEW, path=path)
        return True
