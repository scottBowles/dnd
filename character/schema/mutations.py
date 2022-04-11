import graphene

from nucleus.utils import RelayCUD, ConcurrencyLockActions
from ..models import Language, Script, Feature, Skill, Proficiency, NPC
from ..serializers import (
    LanguageSerializer,
    ScriptSerializer,
    FeatureSerializer,
    SkillSerializer,
    ProficiencySerializer,
    NPCSerializer,
)
from .nodes import (
    LanguageNode,
    ScriptNode,
    FeatureNode,
    SkillNode,
    ProficiencyNode,
    NPCNode,
)


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


class NPCCUD(RelayCUD):
    field = "npc"
    Node = NPCNode
    model = NPC
    serializer_class = NPCSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_id = graphene.String()
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()


class NPCConcurrencyLock(ConcurrencyLockActions):
    field = "npc"
    model = NPC


NPCCUDMutations = NPCCUD().get_mutation_class()
NPCLockMutations = NPCConcurrencyLock().get_mutation_class()


class Mutation(
    LanguageMutations,
    ScriptMutations,
    FeatureMutations,
    SkillMutations,
    ProficiencyMutations,
    NPCCUDMutations,
    NPCLockMutations,
    graphene.ObjectType,
):
    pass
