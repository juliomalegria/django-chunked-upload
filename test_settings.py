"""Minimal settings for the standalone test suite (see runtests.py)."""
import shutil
import tempfile
import atexit

MEDIA_ROOT = tempfile.mkdtemp(prefix='chunked_upload_tests_')
atexit.register(shutil.rmtree, MEDIA_ROOT, ignore_errors=True)

SECRET_KEY = 'tests-only'
DEBUG = False
USE_TZ = True
ROOT_URLCONF = 'test_urls'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'chunked_upload',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
