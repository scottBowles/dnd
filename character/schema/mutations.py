import graphene

from nucleus.utils import RelayCUD
from ..models import Language, Script, Feature, Skill, Proficiency
from ..serializers import (
    LanguageSerializer,
    ScriptSerializer,
    FeatureSerializer,
    SkillSerializer,
    ProficiencySerializer,
)
from .nodes import LanguageNode, ScriptNode, FeatureNode, SkillNode, ProficiencyNode


class LanguageCUD(RelayCUD):
    field = "language"
    Node = LanguageNode
    model = Language
    serializer_class = LanguageSerializer

    class Input:
        name = graphene.String()
        description = graphene.String()
        script = graphene.String()


LanguageMutations = LanguageCUD().get_mutation_class()


class ScriptCUD(RelayCUD):
    field = "script"
    Node = ScriptNode
    model = Script
    serializer_class = ScriptSerializer

    class Input:
        name = graphene.String()


ScriptMutations = ScriptCUD().get_mutation_class()


class Mutation(LanguageMutations, ScriptMutations, graphene.ObjectType):
    pass


class FeatureCUD(RelayCUD):
    field = "feature"
    Node = FeatureNode
    model = Feature
    serializer_class = FeatureSerializer

    class Input:
        name = graphene.String()
        description = graphene.String()


FeatureMutations = FeatureCUD().get_mutation_class()


class SkillCUD(RelayCUD):
    field = "skill"
    Node = SkillNode
    model = Skill
    serializer_class = SkillSerializer

    class Input:
        name = graphene.String()
        description = graphene.String()
        related_ability = graphene.String()
        custom = graphene.Boolean()


SkillMutations = SkillCUD().get_mutation_class()


class ProficiencyCUD(RelayCUD):
    field = "proficiency"
    Node = ProficiencyNode
    model = Proficiency
    serializer_class = ProficiencySerializer

    class Input:
        name = graphene.String()
        description = graphene.String()
        proficiency_type = graphene.String()


ProficiencyMutations = ProficiencyCUD().get_mutation_class()


class Mutation(
    LanguageMutations,
    ScriptMutations,
    FeatureMutations,
    SkillMutations,
    ProficiencyMutations,
    graphene.ObjectType,
):
    pass
