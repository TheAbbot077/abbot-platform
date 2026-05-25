"""Production/staging settings for hosted deployments such as Render.

Local development continues to use config.settings. Render should set:
DJANGO_SETTINGS_MODULE=config.settings_production
"""

from .settings import *  # noqa: F403


DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # noqa: F405

DATABASE_URL = env("DATABASE_URL", default="")  # noqa: F405
if DATABASE_URL:
    DATABASES["default"] = env.db("DATABASE_URL")  # noqa: F405

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)  # noqa: F405

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", default=str(BASE_DIR / "media")))  # noqa: F405

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *[middleware for middleware in MIDDLEWARE if middleware != "django.middleware.security.SecurityMiddleware"],  # noqa: F405
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405

SESSION_COOKIE_HTTPONLY = True
# Render staging commonly serves the frontend and API from different origins.
# Cross-origin session auth needs SameSite=None plus Secure cookies so the
# browser sends the Django session cookie on API requests after login.
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="None")  # noqa: F405
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="None")  # noqa: F405

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env("DJANGO_REFERRER_POLICY", default="same-origin")  # noqa: F405
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),  # noqa: F405
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
