import graphene

from nucleus.utils import RelayCUD
from ..models import Language
from ..serializers import LanguageSerializer
from .nodes import LanguageNode
from graphql_relay import from_global_id


class LanguageCUD(RelayCUD):
    field = "language"
    Node = LanguageNode
    model = Language
    serializer_class = LanguageSerializer

    class Input:
        name = graphene.String()
        description = graphene.String()
        script = graphene.GlobalID()

    def prepare_inputs(self, info, **input):
        script_global_id = input.pop("script", None)
        if script_global_id is not None:
            script_id = from_global_id(script_global_id)[1]
            input["script"] = script_id
        return input


LanguageMutations = LanguageCUD().get_mutation_class()


class Mutation(LanguageMutations, graphene.ObjectType):
    pass
