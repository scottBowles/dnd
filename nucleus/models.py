import datetime
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django_extensions.db.fields import AutoSlugField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.postgres.fields import ArrayField


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
    places_set_in = models.ManyToManyField(
        "place.Place", blank=True, related_name="logs_set_in"
    )

    def __str__(self):
        return self.title or self.url

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.update_from_google()
        super().save(*args, **kwargs)

    def update_from_google(self, overwrite=False):
        """
        Updates the model from google drive — Does NOT save the model
        """
        from nucleus.gdrive import fetch_airel_file

        if self.google_id is None:
            self.set_id_from_url()
        try:
            file_info = fetch_airel_file(self.google_id)
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

    def get_game_date_from_title(self):
        """
        Tries to parse the game date from the title of the log
        Throws ValueError if it can't parse the date
        """
        return datetime.datetime.strptime(self.title[0:10], "%Y-%m-%d").date()

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


class Alias(models.Model):
    name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Entity(
    PessimisticConcurrencyLockModel,
    NameSlugDescriptionModel,
    NotesMarkdownModel,
    ImageIdsModel,
    BaseModel,
):
    logs = models.ManyToManyField(
        GameLog, blank=True, related_name="%(app_label)s_%(class)ss"
    )
    aliases = models.ManyToManyField(
        Alias, blank=True, related_name="%(app_label)s_%(class)ss"
    )

    def __str__(self):
        return self.name

    def most_recent_log_by_title(self):
        return self.logs.order_by("-title").first()

    class Meta:
        abstract = True
