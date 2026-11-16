# Isolated CI settings: never use deployed databases or external services.
from .settings import *

SECRET_KEY = 'ci-only-not-a-production-secret'
DEBUG = False
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
