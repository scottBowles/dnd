"""
Django settings for website project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", default="DjangoSettingsNotGettingSecretKey")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
# DEBUG = os.environ.get("DJANGO_DEBUG", "") != "False"
DEBUG = "RENDER" not in os.environ

ALLOWED_HOSTS = []
# ALLOWED_HOSTS = ["127.0.0.1", ".herokuapp.com"]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# Application definition

INSTALLED_APPS = [
    # "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_extensions",
    "graphene_django",
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "generic_relations",
    "association",
    "character",
    "item",
    "place",
    "quest",
    "race",
    "scientia",
    "nucleus",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "website.middleware.PrintRequestsMiddleware",
]

ROOT_URLCONF = "website.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "website.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# What I had before addin dj_database_url
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql_psycopg2",
#         "NAME": os.environ.get("POSTGRES_DB"),
#         "USER": os.environ.get("POSTGRES_USER"),
#         "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# }
DATABASES = {
    "default": dj_database_url.config(
        # from render.com example (https://render.com/docs/deploy-django):
        #   Feel free to alter this value to suit your needs.
        #   default='postgresql://postgres:postgres@localhost:5432/mysite'
        # from dj_database_url (https://github.com/jacobian/dj-database-url):
        #   postgres://USER:PASSWORD@HOST:PORT/NAME
        default="postgresql://{}:{}@127.0.0.1:5432/{}".format(
            os.environ.get("POSTGRES_USER", None),
            os.environ.get("POSTGRES_PASSWORD", None),
            os.environ.get("POSTGRES_DB", None),
        ),
        conn_max_age=600,
    )
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"

if not DEBUG:
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    # The below disables the browsable api, which isn't useful for the current
    # graphql api and can only slow things down. Remove this if we want it back.
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

CORS_ALLOWED_ORIGINS = (
    [
        "http://localhost:3000",
        "https://aireldnd.onrender.com",
    ]
    if DEBUG
    else ["https://aireldnd.onrender.com"]
)

AUTH_USER_MODEL = "nucleus.User"

DJOSER = {
    "USER_CREATE_PASSWORD_RETYPE": True,
    "SERIALIZERS": {
        "user_create": "nucleus.serializers.UserCreateSerializer",
        "current_user": "nucleus.serializers.UserSerializer",
        "user": "nucleus.serializers.UserSerializer",
    },
}

GRAPHENE = {
    "SCHEMA": "website.schema.schema",
    "ATOMIC_MUTATIONS": True,
}
