# import graphene
import association.schema
import item.schema
import place.schema
import character.schema
import race.schema
import nucleus.schema

# import graphql_jwt


class Query(
    association.schema.Query,
    place.schema.Query,
    item.schema.Query,
    character.schema.Query,
    race.schema.Query,
    nucleus.schema.Query,
    graphene.ObjectType,
):
    pass


class Mutation(
    association.schema.Mutation,
    place.schema.Mutation,
    item.schema.Mutation,
    character.schema.Mutation,
    race.schema.Mutation,
    nucleus.schema.Mutation,
    graphene.ObjectType,
):
    pass
    # token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    # verify_token = graphql_jwt.relay.Verify.Field()
    # refresh_token = graphql_jwt.relay.Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
