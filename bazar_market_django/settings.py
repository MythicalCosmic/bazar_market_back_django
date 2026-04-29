import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")
DEBUG = os.getenv("DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "corsheaders",
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
    "corsheaders.middleware.CorsMiddleware",
    "base.middlewares.responseTimeMiddleware.ResponseTimeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "base.middlewares.forceJsonResponseMiddleware.JSONResponseMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

TELESCOPE_ENABLED = os.getenv("TELESCOPE_ENABLED", "0") == "1"

# DevSMS (phone verification)
DEVSMS_TOKEN = os.getenv("DEVSMS_TOKEN", "")
DEVSMS_URL = "https://devsms.uz/api/send_sms.php"
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 120  # 2 minutes

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# Thermal receipt printer (WebSocket-based)
PRINTER_SECRET = os.getenv("PRINTER_SECRET", "change-me-in-production")

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
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "bazar_market_django.asgi.application"

# Celery
_redis_host = os.getenv("REDIS_URL", "redis://localhost:6379/0").rsplit("/", 1)[0]
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"{_redis_host}/1")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = {
    "cart-abandonment-reminder": {
        "task": "bot.tasks.task_cart_abandonment_reminders",
        "schedule": 3600,
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
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
