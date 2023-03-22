from typing import Optional
from .. import models
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto


@gql.django.type(models.User)
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


@gql.type
class UserQuery:
    user: Optional[User] = gql.django.field()
    users: relay.Connection[User] = gql.django.connection()


@gql.django.input(models.User)
class UserInput:
    username: auto
    password: auto
    first_name: auto
    last_name: auto
    email: auto


@gql.django.partial(models.User)
class UserInputPartial(gql.NodeInput):
    username: auto
    password: auto
    first_name: auto
    last_name: auto
    email: auto


@gql.type
class UserMutation:
    # Eventually we'll want to use something like this, but until we have auth working, we'll leave these off
    pass
    # create_game_log: User = gql.django.create_mutation(UserInput)
    # update_game_log: User = gql.django.update_mutation(UserInputPartial)
    # delete_game_log: User = gql.django.delete_mutation(gql.NodeInput)
