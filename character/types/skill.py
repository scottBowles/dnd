from typing import Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models


@strawberry_django.type(models.Skill)
class Skill(relay.Node):
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@strawberry_django.input(models.Skill)
class SkillInput:
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@strawberry_django.partial(models.Skill)
class SkillInputPartial(strawberry_django.NodeInput):
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@strawberry.type
class SkillQuery:
    skills: DjangoListConnection[Skill] = strawberry_django.connection()

    @strawberry_django.connection(DjangoListConnection[Skill])
    def Skills_connection_filtered(self, name_startswith: str) -> Iterable[Skill]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Skill.objects.filter(name__startswith=name_startswith)


@strawberry.type
class SkillMutation:
    create_skill: Skill = strawberry_django.mutations.create(
        SkillInput, permission_classes=[IsStaff]
    )
    update_skill: Skill = strawberry_django.mutations.update(
        SkillInputPartial, permission_classes=[IsStaff]
    )
    delete_skill: Skill = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
