import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.relay import ListConnectionWithTotalCount

from .. import models


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


@strawberry.type
class UserQuery:
    users: ListConnectionWithTotalCount[User] = strawberry_django.connection()


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
    # Eventually we'll want to use something like this, but until we have auth working, we'll leave these off
    pass
    # create_game_log: User = strawberry_django.mutations.create(UserInput)
    # update_game_log: User = strawberry_django.mutations.update(UserInputPartial)
    # delete_game_log: User = strawberry_django.mutations.delete(strawberry_django.NodeInput)
