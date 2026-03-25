import strawberry_django
from strawberry import auto

from .. import models


@strawberry_django.order_type(models.GameLog)
class GameLogOrder:
    game_date: auto