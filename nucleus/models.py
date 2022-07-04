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


class GameLog(models.Model):
    url = models.CharField(max_length=255)
    name = models.CharField(max_length=512, null=True, blank=True)
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    def __str__(self):
        return self.name or self.url

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.update_from_google()
        super().save(*args, **kwargs)

    def update_from_google(self):
        """
        Updates the model from google drive — Does NOT save the model
        """
        from nucleus.gdrive import fetch_airel_file

        if self.google_id is None:
            self.set_id_from_url()
        try:
            file_info = fetch_airel_file(self.google_id)
            self.name = file_info["name"]
            self.url = file_info["webViewLink"]
        except Exception as e:
            raise e

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
        self.google_id = self.get_id_from_url()


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

    def __str__(self):
        return self.name

    def most_recent_log_by_name(self):
        return self.logs.order_by("-name").first()

    class Meta:
        abstract = True
