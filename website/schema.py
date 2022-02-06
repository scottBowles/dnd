import graphene
import association.schema
import item.schema


class Query(association.schema.Query, item.schema.Query, graphene.ObjectType):
    pass


class Mutation(association.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
