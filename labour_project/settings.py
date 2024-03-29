import os
import sys
import yaml
from .utils import skip_unreadable_post

# Path to here is something like
# .../<repo>/<project_name>/settings.py
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)
PARENT_DIR = os.path.dirname(BASE_DIR)

# The mySociety deployment system works by having a conf directory at the root
# of the repo, containing a general.yml file of options. Use that file if
# present. Obviously you can just edit any part of this file, it is a normal
# Django settings.py file.
try:
    with open(os.path.join(BASE_DIR, 'conf', 'general.yml'), 'r') as fp:
        config = yaml.load(fp, Loader=yaml.SafeLoader)
except: # pragma: no cover
    config = {}

# An EPSG code for what the areas are stored as, e.g. 27700 is OSGB, 4326 for
# WGS84. Optional, defaults to 4326.
MAPIT_AREA_SRID = 27700

# Set this to the maximum distance (in AREA_SRID units) allowed for the within
# parameter to the point call. Optional, defaults to 0 (off).
MAPIT_WITHIN_MAXIMUM = float(config.get('WITHIN_MAXIMUM', 0))
if MAPIT_WITHIN_MAXIMUM.is_integer():
    MAPIT_WITHIN_MAXIMUM = int(MAPIT_WITHIN_MAXIMUM)

# Country is currently one of GB, NO, IT, KE, SA, or ZA.
# Optional; country specific things won't happen if not set.
MAPIT_COUNTRY = "GB"

# A dictionary of IP addresses, User Agents, or functions that should be
# excluded from rate limiting. Optional.
MAPIT_RATE_LIMIT = {}

# A GA code for analytics
GOOGLE_ANALYTICS = config.get('GOOGLE_ANALYTICS', '')

# Django settings for mapit labour_project.

DEBUG = config.get('DEBUG', True)

# (Note that even if DEBUG is true, output_json still sets a
# Cache-Control header with max-age of 28 days.)
if DEBUG and not config.get('DEBUG_USE_MEMCACHE', False):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    CACHE_MIDDLEWARE_SECONDS = 0
else: # pragma: no cover
    try:
        import pymemcache
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
                'LOCATION': '127.0.0.1:11211',
                'TIMEOUT': 86400,
            }
        }
    except ImportError:
        pass
    CACHE_MIDDLEWARE_SECONDS = 86400
    CACHE_MIDDLEWARE_KEY_PREFIX = config.get('MAPIT_DB_NAME')

if config.get('BUGS_EMAIL'):
    SERVER_EMAIL = config['BUGS_EMAIL']
    ADMINS = (
        ('mySociety bugs', config['BUGS_EMAIL']),
    )

if config.get('EMAIL_SUBJECT_PREFIX'):
    EMAIL_SUBJECT_PREFIX = config['EMAIL_SUBJECT_PREFIX']

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config.get('MAPIT_DB_NAME', 'mapit'),
        'USER': config.get('MAPIT_DB_USER', 'mapit'),
        'PASSWORD': config.get('MAPIT_DB_PASS', ''),
        'HOST': config.get('MAPIT_DB_HOST', ''),
        'PORT': config.get('MAPIT_DB_PORT', ''),
    },
    # Have a second connection to the database so we can log
    # progress of CSV import jobs that are occuring in transactions.
    'logging': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config.get('MAPIT_DB_NAME', 'mapit'),
        'USER': config.get('MAPIT_DB_USER', 'mapit'),
        'PASSWORD': config.get('MAPIT_DB_PASS', ''),
        'HOST': config.get('MAPIT_DB_HOST', ''),
        'PORT': config.get('MAPIT_DB_PORT', ''),
    }
}

if config.get('MAPIT_DB_RO_HOST', '') and 'test' not in sys.argv:
    DATABASES['replica'] = {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config.get('MAPIT_DB_NAME', 'mapit'),
        'USER': config.get('MAPIT_DB_USER', 'mapit'),
        'PASSWORD': config.get('MAPIT_DB_PASS', ''),
        'HOST': config['MAPIT_DB_RO_HOST'],
        'PORT': config['MAPIT_DB_RO_PORT'],
        # Should work, but does not appear to (hence sys.argv test above); see
        # https://stackoverflow.com/questions/33941139/test-mirror-default-database-but-no-data
        # 'TEST': {
        #     'MIRROR': 'default',
        # },
    }

    import random
    from .multidb import use_primary

    class PrimaryReplicaRouter(object):
        """A basic primary/replica database router."""
        def db_for_read(self, model, **hints):
            """Randomly pick between default and replica databases, unless the
            request (via middleware) demands we use the primary."""
            if use_primary():
                return 'default'
            return random.choice(['default', 'replica'])

        def db_for_write(self, model, **hints):
            """Always write to the primary database."""
            return 'default'

        def allow_relation(self, obj1, obj2, **hints):
            """Any relation between objects is allowed, as same data."""
            return True

        def allow_migrate(self, db, app_label, model_name=None, **hints):
            """migrate is only ever called on the default database."""
            return True

    DATABASE_ROUTERS = ['labour_project.settings.PrimaryReplicaRouter']

# Make this unique, and don't share it with anybody.
SECRET_KEY = config.get('DJANGO_SECRET_KEY', '')

ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = config.get('CSRF_TRUSTED_ORIGINS', [])

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'
POSTCODES_AVAILABLE = PARTIAL_POSTCODES_AVAILABLE = True

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PARENT_DIR, 'collected_static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# UpdateCacheMiddleware does ETag setting, and
# ConditionalGetMiddleware does ETag checking.
# So we don't want this flag, which runs very
# similar ETag code in CommonMiddleware.
USE_ETAGS = False

MIDDLEWARE = [
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mapit_labour.middleware.LoginOrAPIKeyRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'mapit.middleware.JSONPMiddleware',
    'mapit.middleware.ViewExceptionMiddleware',
]

if config.get('MAPIT_DB_RO_HOST', '') and 'test' not in sys.argv:
    MIDDLEWARE.insert(0, 'labour_project.middleware.force_primary_middleware')

if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'labour_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'labour_project.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': (
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'mapit.context_processors.country',
            'mapit.context_processors.analytics',
        ),
    },
}]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.gis',
    'django.contrib.staticfiles',
    'admin.apps.AdminConfig',
    'mapit_labour',
    'mapit_gb',
    'mapit',
    'django_q',
    'crispy_forms',
    'crispy_forms_gds',
]

if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'skip_unreadable_posts': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_unreadable_post,
        },
    },
    'handlers': {
        'mail_admins': {
            'filters': ['require_debug_false', 'skip_unreadable_posts'],
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        # 'django.db.backends': {
        #     'level': 'DEBUG',
        #     'handlers': ['console'],
        # },
        'mapit_labour': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    },
}

DATE_FORMAT = 'j F Y'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

INTERNAL_IPS = [ '127.0.0.1' ]

LOGIN_URL = "/admin/login/"

FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

LOGIN_REQUIRED_IGNORE_PATHS = [
    r'^/admin/',
    r'/health',
    r'/favicon.ico', # XXX update Apache config so this request never reaches Django
]

API_KEY_AUTH_ALLOWED_PATHS = [
    r'^/uprn/\d+(\.json)?$',
    r'^/addressbase$',

    # Standard MapIt API URL prefixes
    r'^/generations',
    r'^/postcode/',
    r'^/area/',
    r'^/point/',
    r'^/nearest/',
    r'^/areas/',
    r'^/areas$',
    r'^/code/',
]

ADDRESSBASE_RESULTS_LIMIT = config.get('ADDRESSBASE_RESULTS_LIMIT', 100)

Q_CLUSTER = {
    'name': 'mapit_labour',
    'workers': 1,
    'timeout': 60 * 20, # spend 20 minutes on a task before giving up
    'retry': 60 * 25, # wait 25 minutes between attempts to start a task (i.e. tries again 5 minutes after the 20 minute timeout above)
    'max_attempts': 3,
    'orm': 'default',
}

CSV_UPLOAD_DIR = os.path.join(PARENT_DIR, "uploads", "csvs")

CRISPY_ALLOWED_TEMPLATE_PACKS = ["gds"]
CRISPY_TEMPLATE_PACK = "gds"
