from django.db import models


class Armor(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()


class Weapon(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()


class Equipment(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
