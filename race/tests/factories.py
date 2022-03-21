import factory
from factory import fuzzy
from ..models import Race, AbilityScoreIncrease, Trait
from character.models.models import ALIGNMENTS, SIZES, ABILITIES


class AbilityScoreIncreaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AbilityScoreIncrease
        django_get_or_create = ("ability_score",)

    ability_score = fuzzy.FuzzyChoice(ABILITIES, getter=lambda c: c[0])
    increase = factory.Faker("pyint", min_value=1, max_value=6)


class TraitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trait

    name = factory.Faker("name")
    description = factory.Faker("text")


class RaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Race

    name = factory.Faker("name")
    description = factory.Faker("text")
    image_id = factory.Faker("text")
    thumbnail_id = factory.Faker("text")
    age_of_adulthood = factory.Faker("pyint")
    life_expectancy = factory.Faker("pyint")
    alignment = fuzzy.FuzzyChoice(ALIGNMENTS, getter=lambda c: c[0])
    size = fuzzy.FuzzyChoice(SIZES, getter=lambda c: c[0])
    speed = factory.Faker("pyint")

    @factory.post_generation
    def ability_score_increases(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for ability_score_increase in extracted:
                self.ability_score_increases.add(ability_score_increase)

    @factory.post_generation
    def languages(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for language in extracted:
                self.languages.add(language)

    @factory.post_generation
    def traits(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for trait in extracted:
                self.traits.add(trait)

    @factory.post_generation
    def subraces(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for subrace in extracted:
                self.subraces.add(subrace)
