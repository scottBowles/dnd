from strawberry.tools import merge_types

from .entity import *
from .gamelog import *
from .user import *
from .login import *

queries = (GameLogQuery, UserQuery)
mutations = (GameLogMutation, LoginMutation, UserMutation)

Query = merge_types("Query", queries)
Mutation = merge_types("Mutation", mutations)
