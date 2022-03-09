import graphene

from nucleus.utils import RelayCUD
from ..models import Language
from ..serializers import LanguageSerializer
from .nodes import LanguageNode


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


class Mutation(LanguageMutations, graphene.ObjectType):
    pass
