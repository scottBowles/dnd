import factory
from factory import fuzzy
from ..models import Race, Trait
from character.models.models import ALIGNMENTS, SIZES


class TraitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trait

    name = factory.Faker("name")
    description = factory.Faker("text")


class RaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Race

    name = factory.Faker("name")
    age_of_adulthood = factory.Faker("pyint")
    life_expectancy = factory.Faker("pyint")
    alignment = fuzzy.FuzzyChoice(ALIGNMENTS, getter=lambda c: c[0])
    size = fuzzy.FuzzyChoice(SIZES, getter=lambda c: c[0])
    speed = factory.Faker("pyint")

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
