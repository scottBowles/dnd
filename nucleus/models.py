from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    isDM = models.BooleanField(default=False)
