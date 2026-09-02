"""
Django settings for config project (SSTBAVARIA_CCTV — Módulo de Cámaras IA).

Toda la configuración se lee de variables de entorno (os.environ), sin
archivo .env, siguiendo el mismo patrón que el proyecto principal.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


DEBUG = env_bool("DEBUG", default=False)

# SECURITY WARNING: keep the secret key used in production secret! Un valor
# por defecto conocido públicamente (como el que traía este archivo antes)
# permitiría falsificar sesiones/tokens de reseteo de contraseña si alguien
# olvida configurar la variable de entorno — por eso solo se permite un
# fallback en desarrollo local (DEBUG=True); en producción es obligatorio.
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-solo-para-desarrollo-local"
    else:
        raise ImproperlyConfigured(
            "La variable de entorno SECRET_KEY es obligatoria cuando DEBUG=False."
        )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Origen(es) del frontend (Next.js en Vercel) autorizados a llamar esta API.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
# En local (DEBUG) el frontend corre en localhost:3000 sin configurar nada aparte.
if DEBUG:
    CORS_ALLOWED_ORIGINS += ["http://localhost:3000", "http://127.0.0.1:3000"]

if not DEBUG and not ALLOWED_HOSTS:
    # Evita quedar con ALLOWED_HOSTS vacío en producción por falta de config.
    ALLOWED_HOSTS = [".railway.app"]

# URL del dashboard (Next.js en Vercel) — usada para el link "VER SITIO" del
# admin de Django (ver config/urls.py). Si no se configura, cae al primer
# origen de CORS_ALLOWED_ORIGINS o a localhost en desarrollo.
FRONTEND_URL = os.environ.get("FRONTEND_URL") or (
    CORS_ALLOWED_ORIGINS[0] if CORS_ALLOWED_ORIGINS else "http://localhost:3000"
)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "core",
    "camaras_ia",
    "contratistas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    # Fallback para desarrollo local sin Postgres a la mano.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es"

TIME_ZONE = os.environ.get("TIME_ZONE", "America/Bogota")

USE_I18N = True

USE_TZ = True


# Notificaciones por correo (canal "correo" de ReglaAlerta), vía la API HTTP
# de Brevo — ver camaras_ia/notificaciones.py. Sin BREVO_API_KEY el envío
# simplemente falla y queda registrado en el evento (notificacion_detalle),
# no rompe el flujo de recibir_evento_camara.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_REMITENTE_EMAIL = os.environ.get("BREVO_REMITENTE_EMAIL", "alertas@sst-cctv.com")
BREVO_REMITENTE_NOMBRE = os.environ.get("BREVO_REMITENTE_NOMBRE", "SST Bavaria — Cámaras IA")


# Notificaciones push al navegador/celular (Web Push + VAPID) — ver
# core/push.py. Sin las 3 variables configuradas, el envío simplemente no
# hace nada (igual que Brevo sin API key): nunca rompe el flujo que la
# dispara. Generar un par de llaves nuevo con
# `python manage.py generar_claves_vapid`.
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "alertas@sst-cctv.com")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media (Excel original de declaraciones, PDFs de autorización de datos,
# fotos de referencia de cámaras). MEDIA_ROOT/local por defecto — sin
# almacenamiento externo configurado, cualquier archivo subido desaparece
# en el próximo despliegue (el disco de Railway no es persistente entre
# despliegues). Ver USANDO_R2 más abajo para el storage que sí sobrevive.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudflare R2 (API compatible con S3) como storage de archivos subidos,
# para que sobrevivan a los despliegues de Railway. Sin las 4 variables de
# entorno obligatorias configuradas, cae al disco local de arriba — así el
# desarrollo local no necesita una cuenta de Cloudflare. R2_PUBLIC_BASE_URL
# es opcional: sin ella, cada URL de archivo se firma con una expiración
# (1 hora) en vez de exigir que el bucket sea público.
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "")

USANDO_R2 = bool(R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME and R2_ENDPOINT_URL)
if USANDO_R2:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": R2_ENDPOINT_URL,
            "region_name": "auto",
            "signature_version": "s3v4",
            "file_overwrite": False,
            "default_acl": None,
            "querystring_auth": not R2_PUBLIC_BASE_URL,
            "querystring_expire": 3600,
            **(
                {"custom_domain": R2_PUBLIC_BASE_URL.removeprefix("https://").removeprefix("http://")}
                if R2_PUBLIC_BASE_URL
                else {}
            ),
        },
    }

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging: por defecto, con DEBUG=False Django solo intenta mandar los
# errores 500 por correo (mail_admins) y no los imprime en consola — en un
# contenedor eso significa que nunca aparecen en los logs de Railway. Los
# mandamos explícitamente a stdout/stderr para poder diagnosticar.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Django REST Framework
#
# DEFAULT_PERMISSION_CLASSES es IsAuthenticated (no AllowAny): así, cualquier
# vista nueva que alguien agregue sin pensarlo dos veces queda protegida por
# defecto en vez de quedar pública por accidente. Las dos únicas vistas que sí
# deben ser públicas (los endpoints del equipo local, que se autentican con
# su propia API key en vez de con el login de usuario) declaran
# @permission_classes([AllowAny]) explícitamente en camaras_ia/views.py.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Límite de intentos de login por IP, para dificultar fuerza bruta de
        # contraseñas — ver core.throttling.LoginRateThrottle.
        "login": "10/min",
    },
}

# Cabeceras de seguridad HTTP — activas siempre (no solo en producción), no
# tienen costo en desarrollo y evitan que alguien las desactive sin darse
# cuenta al tocar el bloque de abajo.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: le dice al navegador que recuerde usar siempre HTTPS con este
    # host. Empieza en 1 día — subir a 1 año (31536000) una vez confirmado
    # que HTTPS funciona bien en todos los subdominios usados.
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "86400"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)
