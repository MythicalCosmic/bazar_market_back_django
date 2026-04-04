import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")
DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "telescope",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "base",
    "customer",
    "admins",
    "bot",
]

MIDDLEWARE = [
    "base.middlewares.responseTimeMiddleware.ResponseTimeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "base.middlewares.forceJsonResponseMiddleware.JSONResponseMiddleware",
]

TELESCOPE_ENABLED = True

if TELESCOPE_ENABLED:
    MIDDLEWARE.insert(0, "telescope.middleware.TelescopeMiddleware")

ROOT_URLCONF = "bazar_market_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "bazar_market_django.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "bazar_market"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "bazar_secret"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_CONNECT_TIMEOUT": 1,
            "SOCKET_TIMEOUT": 1,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


ASGI_APPLICATION = "bazar_market_django.asgi.application"


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


TELESCOPE = {
    "ENABLED": TELESCOPE_ENABLED,
    "WATCHERS": {
        "RequestWatcher": {"enabled": True},
        "QueryWatcher": {"enabled": True, "slow_threshold": 50},
        "ExceptionWatcher": {"enabled": True},
        "ModelWatcher": {"enabled": False},
        "LogWatcher": {"enabled": False},
        "CacheWatcher": {"enabled": False},
        "RedisWatcher": {"enabled": False},
        "MailWatcher": {"enabled": False},
        "ViewWatcher": {"enabled": False},
        "EventWatcher": {"enabled": False},
        "CommandWatcher": {"enabled": False},
        "GateWatcher": {"enabled": False},
        "NotificationWatcher": {"enabled": False},
        "DumpWatcher": {"enabled": False},
        "ClientRequestWatcher": {"enabled": False},
        "ScheduleWatcher": {"enabled": False},
        "BatchWatcher": {"enabled": False},
    },
}