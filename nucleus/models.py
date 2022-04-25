from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django_extensions.db.fields import AutoSlugField
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.postgres.fields import ArrayField


class User(AbstractUser):
    isDM = models.BooleanField(default=False)


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

    image_ids = ArrayField(models.CharField(max_length=255), default=list)
    thumbnail_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        abstract = True


class NotesMarkdownModel(models.Model):
    """
    NotesMarkdownModel

    An abstract base class model that provides notes and markdown fields.
    """

    markdown_notes = models.TextField(default="")

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


class Entity(
    PessimisticConcurrencyLockModel,
    NameSlugDescriptionModel,
    NotesMarkdownModel,
    ImageIdsModel,
    BaseModel,
):
    def __str__(self):
        return self.name

    class Meta:
        abstract = True
