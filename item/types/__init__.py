from strawberry.tools import merge_types

from .artifact import *
from .item import *

queries = (ArtifactQuery, ItemQuery)
mutations = (ArtifactMutation, ItemMutation)

Query = merge_types("Query", queries)
Mutation = merge_types("Mutation", mutations)
