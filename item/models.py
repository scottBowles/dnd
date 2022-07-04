from django.db import models
from graphql_relay import to_global_id
from nucleus.models import Entity

"""
One table holds all of our Items, which can have any number of trait sets associated with it.
Each trait set has its own proxy model and manager for relevant methods.
"""


class Item(Entity):
    def __str__(self):
        return self.name

    def global_id(self):
        return to_global_id("ItemNode", self.id)


class Artifact(Entity):
    items = models.ManyToManyField(Item, related_name="artifacts", blank=True)
    notes = models.TextField(null=True, blank=True)

    def global_id(self):
        return to_global_id("ArtifactNode", self.id)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Artifact {self.name}>"

    def __getattr__(self, attr):
        if attr == "name":
            return self.get_name()
        return super().__getattr__(attr)

    def get_name(self):
        return self.name or self.items.first().name


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
