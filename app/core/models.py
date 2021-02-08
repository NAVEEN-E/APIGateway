from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.core.exceptions import ValidationError
from uuid import uuid4
# import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, \
    PermissionsMixin
from core.validators import (
    validate_json_object_not_empty,
)
from core.managers import Manager


class Nameable(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True


class Extendable(models.Model):
    # The Django convention is to use empty string '' (via blank=True) and not
    # NULL (via null=True) for string-based fields like CharField and TextField
    # to indicate that the field is not set. But given that this is the JSON
    # representation of an object, we expect to  show NULL in instances where
    # ext is not set in the API.
    ext = models.TextField(
        blank=True,
        null=True,
        validators=[validate_json_object_not_empty],
    )

    class Meta:
        abstract = True


class Notes(models.Model):
    notes = models.TextField(
        blank=True,
        max_length=4000,
        validators=[MinLengthValidator(2)],
    )

    class Meta:
        abstract = True


class Resource(Nameable, Notes):
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
    )
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """Creates and saves a new user"""
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """Custome user model that supports using email instead of username"""
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    address = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    picture = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    roles = models.ForeignKey(
        'Role',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        default=None,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    otp = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'


class AppModule(Resource, Extendable):
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    user = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='app_modules',
        through='AppModuleUserMapping',
    )

    dashboard_url = models.URLField(blank=True)
    login_url = models.URLField(blank=True)

    def __str__(self):
        return str(self.name)


class AppModuleUserMapping(models.Model):
    apmodule = models.ForeignKey(
        'AppModule',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
    )
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
    )


class Role(models.Model):
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
    )
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return str(self.name)


class ITTModel(models.Model):
    """
    Intended to be used for any overrides over the object instances
    across models (such as saving default values
    based on other fields, etc.).
    """

    objects = Manager()

    def save(self, *args, **kwargs):
        self.assign_default()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
