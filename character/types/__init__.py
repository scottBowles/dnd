from strawberry.tools import merge_types

from .feature import *
from .language import *
from .npc import *
from .proficiency import *
from .script import *
from .skill import *

queries = (
    FeatureQuery,
    LanguageQuery,
    NpcQuery,
    ProficiencyQuery,
    ScriptQuery,
    SkillQuery,
)
mutations = (
    FeatureMutation,
    LanguageMutation,
    NpcMutation,
    ProficiencyMutation,
    ScriptMutation,
    SkillMutation,
)

Query = merge_types("Query", queries)
Mutation = merge_types("Mutation", mutations)
