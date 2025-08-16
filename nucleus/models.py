from django.contrib.postgres.indexes import GinIndex
import datetime
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django_extensions.db.fields import AutoSlugField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q
from django.utils.functional import cached_property

from django.conf import settings
from django.forms.models import model_to_dict


class ModelDiffMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__initial = self._dict
        self.__changed_attributes = {}

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    @property
    def changed_values(self):
        return list(self.__changed_attributes.keys())

    @property
    def diff(self):
        initial_fields = self.__initial
        current_fields = self._dict
        diffs = [
            (k, (v, current_fields[k]))
            for k, v in list(initial_fields.items())
            if not v == current_fields[k]
        ]
        return dict(diffs)

    def is_changing(self, field_name):
        return bool(self.diff.get(field_name, False))

    def is_adding(self, field_name):
        initial_fields = self.__initial
        return self.is_changing(field_name) and not initial_fields.get(field_name)

    def is_removing(self, field_name):
        return self.is_changing(field_name) and not getattr(self, field_name)

    def has_changed(self, field_name):
        return bool(self.__changed_attributes.get(field_name, False))

    def previous_value(self, field_name):
        value = self.__changed_attributes.get(field_name)
        if value:
            return value[0]

    def has_added(self, field_name):
        if self.__changed_attributes.get(field_name, False):
            return self.__changed_attributes.get(field_name)[0] is None
        return False

    def save(self, *args, **kwargs):
        self.__changed_attributes = self.diff
        super().save(*args, **kwargs)
        self.__initial = self._dict


class User(AbstractUser):
    isDM = models.BooleanField(default=False)
    last_activity = models.DateTimeField(default=timezone.now)


class CreatableModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class UpdatableModel(models.Model):
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(CreatableModel, UpdatableModel):
    class Meta:
        abstract = True


class NameDescriptionModel(models.Model):
    """
    NameDescriptionModel

    An abstract base class model that provides name and description fields.
    """

    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True, null=True)

    class Meta:
        abstract = True


class NameSlugDescriptionModel(NameDescriptionModel):
    """
    NameSlugDescriptionModel

    An abstract base class model that provides name and description fields
    and a self-managed "slug" field that populates from the name.

    .. note ::
        If you want to use custom "slugify" function, you could
        define ``slugify_function`` which then will be used
        in :py:class:`AutoSlugField` to slugify ``populate_from`` field.

        See :py:class:`AutoSlugField` for more details.
    """

    slug = AutoSlugField(_("slug"), populate_from="name", unique=True, blank=True)

    def get_absolute_url(self):
        # return reverse("model_detail", kwargs={"pk": self.pk})
        raise NotImplementedError

    class Meta:
        abstract = True


class ImageIdsModel(models.Model):
    """
    ImageIdsModel

    An abstract base class model that provides image ids fields.
    """

    image_ids = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    thumbnail_id = models.CharField(max_length=255, blank=True, null=True)

    def add_image(self, imageId):
        self.image_ids.append(imageId)
        self.save()

    def thumbnail(self):
        try:
            return self.thumbnail_id or self.image_ids[0]
        except IndexError:
            return None

    class Meta:
        abstract = True


class NotesMarkdownModel(models.Model):
    """
    NotesMarkdownModel

    An abstract base class model that provides notes and markdown fields.
    """

    markdown_notes = models.TextField(default="", blank=True, null=True)

    class Meta:
        abstract = True


class PessimisticConcurrencyLockModel(models.Model):
    """
    PessimisticConcurrencyLockModel

    An abstract base class model that provides pessimistic concurrency lock.
    """

    lock_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_lock_user",
    )
    lock_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def lock(self, user):
        if self.lock_user != user and self.lock_user is not None:
            raise ValueError(
                f"This object is locked by another user: {self.lock_user}."
            )
        self.lock_user = user
        self.lock_time = timezone.now()
        self.save()
        return self

    def release_lock(self, user):
        if (
            self.lock_user != user
            and self.lock_user is not None
            and not self.lock_user.is_superuser
        ):
            raise ValueError(
                f"This object is locked by another user: {self.lock_user}. Cannot release lock."
            )
        self.lock_user = None
        self.lock_time = None
        self.save()
        return self


class GameLog(PessimisticConcurrencyLockModel, models.Model):
    url = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=512, null=True, blank=True)
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    google_created_time = models.DateTimeField(null=True, blank=True)
    game_date = models.DateTimeField(null=True, blank=True)
    brief = models.TextField(null=True, blank=True)
    synopsis = models.TextField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    places_set_in = models.ManyToManyField(
        "place.Place", blank=True, related_name="logs_set_in"
    )
    audio_session_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes for this session's audio, used for transcription context.",
    )
    last_game_log = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_game_logs",
        help_text="The previous game log (used for context in transcription).",
    )
    generated_log_text = models.TextField(
        null=True, blank=True, help_text="Narrative session log generated by LLM."
    )
    session_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Sequential session number for ordering and reference",
    )

    def __str__(self):
        return self.title or self.url

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.update_from_google()
            # Default last_game_log to the most recently created GameLog (excluding self)
            if not self.last_game_log:
                latest_log = (
                    GameLog.objects.exclude(pk=self.pk).order_by("-game_date").first()
                )
                if latest_log:
                    self.last_game_log = latest_log
        super().save(*args, **kwargs)

    def update_from_google(self, overwrite=False):
        """
        Updates the model from google drive — Does NOT save the model
        """
        from nucleus.gdrive import fetch_airel_file

        if not self.google_id:
            self.set_id_from_url()
        try:
            file_info = fetch_airel_file(self.google_id)
            if overwrite or not self.title:
                self.title = file_info["name"]
            if overwrite or not self.url:
                self.url = file_info["webViewLink"]
            if overwrite or not self.google_created_time:
                self.google_created_time = file_info["createdTime"]
            if overwrite or not self.game_date:
                try:
                    self.game_date = self.get_game_date_from_title()
                except ValueError:
                    self.game_date = file_info["createdTime"]

        except Exception as e:
            raise e

    def update_from_google_file_info(self, file_info, overwrite=False):
        """
        Updates the model from google drive file info — Does NOT save the model
        """
        if self.google_id is None:
            self.set_id_from_url()
        try:
            if overwrite or self.title is None:
                self.title = file_info["name"]
            if overwrite or self.url is None:
                self.url = file_info["webViewLink"]
            if overwrite or self.google_created_time is None:
                self.google_created_time = file_info["createdTime"]
            if overwrite or self.game_date is None:
                try:
                    self.game_date = self.get_game_date_from_title()
                except ValueError:
                    self.game_date = file_info["createdTime"]

        except Exception as e:
            raise e

    @cached_property
    def log_text(self):
        """
        Returns the generated log text if it exists, otherwise falls back to the Google Doc text.
        """
        # if self.generated_log_text and self.generated_log_text.strip():
        #     return self.generated_log_text

        from nucleus.gdrive import fetch_airel_file_text

        return fetch_airel_file_text(self.google_id)

    def copy_text_for_summary(self):
        if not self.google_id:
            return ""
        return (
            'Make the following text 70% shorter without losing any content. Be especially sure to retain all events, characters, places, items, and essential details that are mentioned in the log.\n\nText: """\n\n'
            + self.log_text
            + '\n"""\n\nSummary:\n'
        )

    def copy_text_for_ai_suggestions(self):
        if not self.google_id:
            return ""
        return (
            '''
            Given the following game log from a role playing game, give it a creative episode title of a few words and a brief description of a few sentences. Also list all places, characters, races, associations, and items that are mentioned. If you are not sure which something is, include it in both. The response should be in the form of a json object with the following keys: "title", "brief", "places", "characters", "races", "associations", "items". For example:
            '{"title":"My Title","brief":"The Branch, lead by Ego, invents AI using the ReDream. On their way to Hielo, they have to fight off void spiders. They make it to Hielo, and leave the nascent AI to mature.","places":["Hielo"],"characters":["Ego","Void Spiders","AI"],"races":["Void Spiders","AI"],"associations":["The Branch"],"items":["ReDream"]}'
            Text:
            """
            '''
            + self.log_text
            + '''
            """
            Response:
            '''
        )

    def copy_text_for_ai_titles(self):
        if not self.google_id:
            return ""
        return (
            '''
            Given the following game log from a role playing game, provide five possible one-phrase episode titles. One title should be descriptive, one evocative, one pithy, one funny, and one entertaining. The response should be a json object with the key "titles" and the value as an array of five strings. For example:
            '{"titles":["My Title","My Title","My Title","My Title","My Title"]}'
            Text:
            """
            '''
            + self.log_text
            + '''
            """
            Response:
            '''
        )

    def get_game_date_from_title(self):
        """
        Tries to parse the game date from the title of the log
        Throws ValueError if it can't parse the date
        """
        date = datetime.datetime.strptime(self.title[0:10], "%Y-%m-%d")
        return timezone.make_aware(date, datetime.timezone.utc)

    @staticmethod
    def get_id_from_url(url):
        split_url = url.split("/")
        if len(split_url) == 1:
            return split_url[0]
        else:
            try:
                d_index = split_url.index("d")
                id_index = d_index + 1
                return split_url[id_index]
            except ValueError:
                raise ValueError(
                    f"Could not find id in url: {url}. Make sure the url is a google drive url."
                )

    def set_id_from_url(self):
        self.google_id = self.get_id_from_url(self.url)

    def get_text(self):
        from nucleus.gdrive import fetch_airel_file_text

        text = fetch_airel_file_text(self.google_id)
        return text

    def get_ai_log_suggestions(self):
        from nucleus.ai_helpers import openai_summarize_text_chat
        import json

        if self.ailogsuggestion_set.count() > 0:
            return self.ailogsuggestion_set.first()

        text = self.get_text()
        response = openai_summarize_text_chat(text)
        json_res: str = response["choices"][0]["text"]

        try:
            data = json.loads(json_res)

            ret = {
                "title": data["title"],
                "brief": data["brief"],
                "synopsis": data["synopsis"],
                "places": data["places"].split(", "),
                "characters": data["characters"].split(", "),
                "associations": data["associations"].split(", "),
                "items": data["items"].split(", "),
                "races": data["races"].split(", "),
            }
            aiLogSuggestion = AiLogSuggestion.objects.create(**ret)
            return aiLogSuggestion
        except Exception as e:
            print(e)
            raise Exception(f"Could not parse json: {json_res}")

    def get_previous_log(self):
        """
        Returns the previous GameLog by game_date, or None if not found.
        """
        try:
            return (
                GameLog.objects.filter(
                    game_date__isnull=False, game_date__lt=self.game_date
                )
                .exclude(pk=self.pk)
                .latest("game_date")
            )
        except GameLog.DoesNotExist:
            return None


class CombinedAiLogSuggestion:
    def __init__(self, log):
        self.log = log
        self.suggestions = log.ailogsuggestion_set.all()

    def consolidated_str_field(self, prop):
        return [
            getattr(s, prop, None)
            for s in self.suggestions
            if getattr(s, prop, None) is not None
        ]

    @property
    def titles(self):
        return self.consolidated_str_field("title")

    @property
    def briefs(self):
        return self.consolidated_str_field("brief")

    @property
    def synopses(self):
        return self.consolidated_str_field("synopsis")

    def consolidated_suggested_names_for_prop(self, prop):
        return list(
            set(
                [
                    el
                    for suggestion in self.suggestions
                    for el in getattr(suggestion, prop, []) or []
                    if el is not None
                ]
            )
        )

    @property
    def places(self):
        return self.consolidated_suggested_names_for_prop("places")

    @property
    def characters(self):
        return self.consolidated_suggested_names_for_prop("characters")

    @property
    def races(self):
        return self.consolidated_suggested_names_for_prop("races")

    @property
    def associations(self):
        return self.consolidated_suggested_names_for_prop("associations")

    @property
    def items(self):
        return self.consolidated_suggested_names_for_prop("items")

    @property
    def all_suggested_names(self):
        all_names = [
            name
            for entity_list in [
                self.associations,
                self.characters,
                self.items,
                self.places,
                self.races,
            ]
            for name in entity_list
            if name is not None
        ]
        return list(set(all_names))

    def found_suggested_for_model(self, model):
        return model.objects.filter(
            Q(name__in=self.all_suggested_names)
            | Q(aliases__name__in=self.all_suggested_names)
        ).distinct()

    @property
    def found_places(self):
        from place.models import Place

        return self.found_suggested_for_model(Place)

    @property
    def found_characters(self):
        from character.models import Character

        return self.found_suggested_for_model(Character)

    @property
    def found_items(self):
        from item.models import Item

        return self.found_suggested_for_model(Item)

    @property
    def found_artifacts(self):
        from item.models import Artifact

        return self.found_suggested_for_model(Artifact)

    @property
    def found_races(self):
        from race.models import Race

        return self.found_suggested_for_model(Race)

    @property
    def found_associations(self):
        from association.models import Association

        return self.found_suggested_for_model(Association)


class AiLogSuggestion(CreatableModel, models.Model):
    log = models.ForeignKey(GameLog, on_delete=models.CASCADE)
    title = models.CharField(max_length=512, null=True, blank=True)
    brief = models.TextField(null=True, blank=True)
    synopsis = models.TextField(null=True, blank=True)
    associations = ArrayField(models.CharField(max_length=512), null=True, blank=True)
    characters = ArrayField(models.CharField(max_length=512), null=True, blank=True)
    items = ArrayField(models.CharField(max_length=512), null=True, blank=True)
    places = ArrayField(models.CharField(max_length=512), null=True, blank=True)
    races = ArrayField(models.CharField(max_length=512), null=True, blank=True)

    @property
    def all_suggested_entity_names(self):
        entity_lists = [
            self.associations,
            self.characters,
            self.items,
            self.places,
            self.races,
        ]
        return [
            name
            for entity_list in entity_lists
            for name in entity_list
            if name is not None
        ]

    def found_suggested_for_model(self, model):
        return model.objects.filter(
            Q(name__in=self.all_suggested_entity_names)
            | Q(aliases__name__in=self.all_suggested_entity_names)
        ).distinct()

    @staticmethod
    def found_suggested_for_model_and_suggested_names(model, suggested_names):
        return model.objects.filter(
            Q(name__in=suggested_names) | Q(aliases__name__in=suggested_names)
        ).distinct()

    @property
    def found_artifacts(self):
        from item.models import Artifact

        return self.found_suggested_for_model(Artifact)

    @property
    def found_associations(self):
        from association.models import Association

        return self.found_suggested_for_model(Association)

    @property
    def found_characters(self):
        from character.models import Character

        return self.found_suggested_for_model(Character)

    @property
    def found_items(self):
        from item.models import Item

        return self.found_suggested_for_model(Item)

    @property
    def found_places(self):
        from place.models import Place

        return self.found_suggested_for_model(Place)

    @property
    def found_races(self):
        from race.models import Race

        return self.found_suggested_for_model(Race)


class Alias(models.Model):
    name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)

    @property
    def entity(self):
        return (
            self.base_characters.first()
            or self.base_places.first()
            or self.base_items.first()
            or self.base_artifacts.first()
            or self.base_associations.first()
            or self.base_races.first()
        )

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            GinIndex(
                fields=["name"],
                name="alias_name_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]


class Entity(
    ModelDiffMixin,
    PessimisticConcurrencyLockModel,
    NameSlugDescriptionModel,
    NotesMarkdownModel,
    ImageIdsModel,
    BaseModel,
):
    logs = models.ManyToManyField(GameLog, blank=True, related_name="%(class)ss")
    aliases = models.ManyToManyField(Alias, blank=True, related_name="base_%(class)ss")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # if name changed, get or create primary alias
        if (
            self.is_changing("name")
            or self.aliases.filter(is_primary=True).count() == 0
        ):
            primary_alias = self.aliases.filter(is_primary=True).first()
            if primary_alias:
                primary_alias.name = self.name
                primary_alias.save()
            else:
                new_alias = Alias.objects.create(name=self.name, is_primary=True)
                self.aliases.add(new_alias)

    def __str__(self):
        return self.name

    def most_recent_log_by_title(self):
        return self.logs.order_by("-title").first()

    class Meta:
        abstract = True


class SessionAudio(BaseModel):
    """Audio file associated with a D&D game session."""

    file = models.FileField(upload_to="audio/")
    gamelog = models.ForeignKey(
        GameLog, on_delete=models.CASCADE, related_name="session_audio_files"
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    transcription_status = models.CharField(
        max_length=20,
        choices=[
            ("not_transcribed", "Not Transcribed"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="not_transcribed",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.original_filename} ({self.gamelog})"

    @property
    def file_size_mb(self):
        """Get file size in MB."""
        if self.file and hasattr(self.file, "size"):
            return round(self.file.size / (1024 * 1024), 2)
        return None
