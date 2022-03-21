import factory
from factory import fuzzy
from ..models import (
    NPC,
    SIZES,
    ABILITIES,
    Feature,
    Skill,
    Proficiency,
    Language,
    Script,
)


class NPCFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NPC

    name = factory.Faker("name")
    description = factory.Faker("text")
    size = fuzzy.FuzzyChoice(SIZES, getter=lambda c: c[0])
    image_id = factory.Faker("text")
    thumbnail_id = factory.Faker("text")

    @factory.post_generation
    def features_and_traits(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for feature in extracted:
                self.features_and_traits.add(feature)

    @factory.post_generation
    def proficiencies(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for proficiency in extracted:
                self.proficiencies.add(proficiency)


class FeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feature

    name = factory.Faker("name")
    description = factory.Faker("text")


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill

    name = factory.Faker("name")
    description = factory.Faker("text")
    related_ability = fuzzy.FuzzyChoice(ABILITIES, getter=lambda c: c[0])
    custom = factory.Faker("boolean")


class ProficiencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proficiency

    name = factory.Faker("name")
    description = factory.Faker("text")
    proficiency_type = fuzzy.FuzzyChoice(
        Proficiency.PROFICIENCY_TYPES, getter=lambda c: c[0]
    )


class ScriptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Script

    name = factory.Faker("name")


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Language

    name = factory.Faker("name")
    description = factory.Faker("text")
    script = factory.SubFactory(ScriptFactory)


# class PlaceFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Place

#     place_type = factory.Iterator(Place.PLACE_TYPES, getter=lambda c: c[0])
#     name = factory.Faker("name")
#     description = factory.Faker("text")
#     population = factory.Faker("pyint")


# class AssociationFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Association

#     name = factory.Faker("name")
#     description = factory.Faker("text")


# class PlaceAssociationFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = PlaceAssociation

#     place = factory.SubFactory(PlaceFactory)
#     association = factory.SubFactory(AssociationFactory)
#     notes = factory.Faker("text")


# class ExportFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Export

#     name = factory.Faker("name")
#     description = factory.Faker("text")


# class PlaceExportFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = PlaceExport

#     place = factory.SubFactory(PlaceFactory)
#     export = factory.SubFactory(ExportFactory)
#     significance = fuzzy.FuzzyChoice(PlaceExport.SIGNIFICANCE, getter=lambda c: c[0])


# class RaceFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Race

#     name = factory.Faker("name")


# class PlaceRaceFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = PlaceRace

#     place = factory.SubFactory(PlaceFactory)
#     race = factory.SubFactory(RaceFactory)
#     percent = factory.Faker("pyfloat", left_digits=2, right_digits=2, positive=True)
#     notes = factory.Faker("text")
