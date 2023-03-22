from typing import Iterable, Optional
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models


@gql.django.type(models.Skill)
class Skill(relay.Node):
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@gql.django.input(models.Skill)
class SkillInput:
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@gql.django.partial(models.Skill)
class SkillInputPartial(gql.NodeInput):
    name: auto
    description: auto
    related_ability: auto
    custom: auto


@gql.type
class SkillQuery:
    skill: Optional[Skill] = gql.django.field()
    skills: relay.Connection[Skill] = gql.django.connection()

    @gql.django.connection
    def Skills_connection_filtered(self, name_startswith: str) -> Iterable[Skill]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Skill.objects.filter(name__startswith=name_startswith)


@gql.type
class SkillMutation:
    create_skill: Skill = gql.django.create_mutation(SkillInput)
    update_skill: Skill = gql.django.update_mutation(SkillInputPartial)
    delete_skill: Skill = gql.django.delete_mutation(gql.NodeInput)
