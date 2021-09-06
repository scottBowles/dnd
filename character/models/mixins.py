from django.db import models

class HitDieMixin(models.Model):
    class HitDie(models.TextChoices):
        D4 = "d4", "d4"
        D6 = "d6", "d6"
        D8 = "d8", "d8"
        D10 = "d10", "d10"
        D12 = "d12", "d12"
        D20 = "d20", "d20"

    hit_die = models.CharField(
        max_length=3, choices=HitDie.choices, null=True, blank=True
    )

    class Meta:
        abstract = True
