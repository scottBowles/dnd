import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from .nodes import (
    NPCNode,
    FeatureNode,
    SkillNode,
    LanguageNode,
    ScriptNode,
    ProficiencyNode,
)


class NPCQuery(graphene.ObjectType):
    npc = relay.Node.Field(NPCNode)
    npcs = DjangoFilterConnectionField(NPCNode)


class FeatureQuery(graphene.ObjectType):
    feature = relay.Node.Field(FeatureNode)
    features = DjangoFilterConnectionField(FeatureNode)


class SkillQuery(graphene.ObjectType):
    skill = relay.Node.Field(SkillNode)
    skills = DjangoFilterConnectionField(SkillNode)


class LanguageQuery(graphene.ObjectType):
    language = relay.Node.Field(LanguageNode)
    languages = DjangoFilterConnectionField(LanguageNode)


class ScriptQuery(graphene.ObjectType):
    script = relay.Node.Field(ScriptNode)
    scripts = DjangoFilterConnectionField(ScriptNode)


class ProficiencyQuery(graphene.ObjectType):
    proficiency = relay.Node.Field(ProficiencyNode)
    proficiencies = DjangoFilterConnectionField(ProficiencyNode)


class Query(
    NPCQuery,
    FeatureQuery,
    SkillQuery,
    ProficiencyQuery,
    LanguageQuery,
    ScriptQuery,
    graphene.ObjectType,
):
    pass
