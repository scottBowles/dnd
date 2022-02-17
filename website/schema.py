import graphene
import association.schema
import item.schema
import place.schema


class Query(
    association.schema.Query, place.schema.Query, item.schema.Query, graphene.ObjectType
):
    pass


class Mutation(
    association.schema.Mutation,
    place.schema.Mutation,
    item.schema.Mutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
