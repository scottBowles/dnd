from django.db import models
from nucleus.models import Entity

"""
One table holds all of our Items, which can have any number of trait sets associated with it.
Each trait set has its own proxy model and manager for relevant methods.
"""


class Item(Entity):
    def __str__(self):
        return self.name


class ArtifactTraits(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="artifact")
    notes = models.TextField(default="", blank=True)


class ArtifactManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(artifact__isnull=False)


class Artifact(Item):
    objects = ArtifactManager()

    class Meta:
        proxy = True
        verbose_name_plural = "Artifact"

    def save(self, *args, **kwargs):
        if self.artifact is None:
            raise TypeError("Artifact has no artifact traits.")
        super().save(*args, **kwargs)


class ArmorTraits(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="armor")
    ac_bonus = models.IntegerField(default=0, blank=True)


class ArmorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(armor__isnull=False)


class Armor(Item):
    objects = ArmorManager()

    class Meta:
        proxy = True
        verbose_name_plural = "Armor"

    def save(self, *args, **kwargs):
        if self.armor is None:
            raise TypeError("Armor has no armor traits.")
        super().save(*args, **kwargs)


class WeaponTraits(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="weapon")
    attack_bonus = models.IntegerField(default=0, blank=True)


class WeaponManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(weapon__isnull=False)


class Weapon(Item):
    objects = WeaponManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        if self.weapon is None:
            raise TypeError("Weapon has no weapon traits.")
        super().save(*args, **kwargs)


class EquipmentTraits(models.Model):
    item = models.OneToOneField(
        Item, on_delete=models.CASCADE, related_name="equipment"
    )
    brief_description = models.TextField(default="", blank=True)


class EquipmentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(equipment__isnull=False)


class Equipment(Item):
    objects = EquipmentManager()

    class Meta:
        proxy = True
        verbose_name_plural = "Equipment"

    def save(self, *args, **kwargs):
        if self.equipment is None:
            raise TypeError("Equipment has no equipment traits.")
        super().save(*args, **kwargs)
