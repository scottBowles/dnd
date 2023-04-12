from strawberry.tools import merge_types
from strawberry_django_plus import gql
import strawberry
from gqlauth.user.queries import UserQueries
from gqlauth.user import relay as mutations


from association.types import AssociationQuery, AssociationMutation
from character.types import (
    FeatureQuery,
    LanguageQuery,
    CharacterQuery,
    ProficiencyQuery,
    ScriptQuery,
    SkillQuery,
    FeatureMutation,
    LanguageMutation,
    CharacterMutation,
    ProficiencyMutation,
    ScriptMutation,
    SkillMutation,
)
from item.types import ArtifactQuery, ItemQuery, ArtifactMutation, ItemMutation
from nucleus.types import (
    GameLogQuery,
    UserQuery,
    GameLogMutation,
    LoginMutation,
    UserMutation,
)
from place.types import PlaceQuery, PlaceMutation, ExportQuery, ExportMutation
from race.types import (
    AbilityScoreIncreaseQuery,
    RaceQuery,
    TraitQuery,
    AbilityScoreIncreaseMutation,
    RaceMutation,
    TraitMutation,
)


@strawberry.type
class GqlAuthMutation:
    # include what-ever mutations you want.
    verify_token = mutations.VerifyToken.field
    # update_account = mutations.UpdateAccount.field
    # archive_account = mutations.ArchiveAccount.field
    # delete_account = mutations.DeleteAccount.field
    # password_change = mutations.PasswordChange.field
    # swap_emails = mutations.SwapEmails.field
    # captcha = Captcha.field
    # token_auth = mutations.ObtainJSONWebToken.field
    # register = mutations.Register.field
    # verify_account = mutations.VerifyAccount.field
    # resend_activation_email = mutations.ResendActivationEmail.field
    # send_password_reset_email = mutations.SendPasswordResetEmail.field
    # password_reset = mutations.PasswordReset.field
    # password_set = mutations.PasswordSet.field
    refresh_token = mutations.RefreshToken.field
    revoke_token = mutations.RevokeToken.field
    # verify_secondary_email = mutations.VerifySecondaryEmail.field


queries = (
    AbilityScoreIncreaseQuery,
    ArtifactQuery,
    AssociationQuery,
    ExportQuery,
    FeatureQuery,
    GameLogQuery,
    ItemQuery,
    LanguageQuery,
    CharacterQuery,
    PlaceQuery,
    ProficiencyQuery,
    RaceQuery,
    ScriptQuery,
    SkillQuery,
    TraitQuery,
    UserQuery,
    UserQueries,  # new from gqlauth
)

mutations = (
    AbilityScoreIncreaseMutation,
    ArtifactMutation,
    AssociationMutation,
    ExportMutation,
    FeatureMutation,
    GameLogMutation,
    GqlAuthMutation,
    ItemMutation,
    LanguageMutation,
    LoginMutation,
    CharacterMutation,
    PlaceMutation,
    ProficiencyMutation,
    RaceMutation,
    ScriptMutation,
    SkillMutation,
    TraitMutation,
    UserMutation,
)

Query = merge_types("Query", queries)
Mutation = merge_types("Mutation", mutations)

schema = gql.Schema(query=Query, mutation=Mutation)
