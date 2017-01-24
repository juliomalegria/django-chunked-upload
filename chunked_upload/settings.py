from importlib import import_module
from datetime import timedelta

from django.conf import settings

try:
    from django.core.serializers.json import DjangoJSONEncoder
except ImportError:
    try:
        # Deprecated class name (for backwards compatibility purposes)
        from django.core.serializers.json import (
            DateTimeAwareJSONEncoder as DjangoJSONEncoder
        )
    except ImportError:
        raise ImportError('Dude! what version of Django are you using?')


# How long after creation the upload will expire
DEFAULT_EXPIRATION_DELTA = timedelta(days=1)
EXPIRATION_DELTA = getattr(settings, 'CHUNKED_UPLOAD_EXPIRATION_DELTA',
                           DEFAULT_EXPIRATION_DELTA)


# Path where uploading files will be stored until completion
DEFAULT_UPLOAD_PATH = 'chunked_uploads/%Y/%m/%d'
UPLOAD_PATH = getattr(settings, 'CHUNKED_UPLOAD_PATH', DEFAULT_UPLOAD_PATH)


# Storage system
storagename = getattr(settings, 'CHUNKED_UPLOAD_STORAGE_CLASS', None)
if storagename:
    path, cls = storagename.rsplit(".", maxsplit=1)
    storagemodule = import_module(path)
    STORAGE = getattr(storagemodule, cls, lambda: None)()
else:
    STORAGE = (lambda: None)()

# Boolean that defines if the ChunkedUpload model is abstract or not
ABSTRACT_MODEL = getattr(settings, 'CHUNKED_UPLOAD_ABSTRACT_MODEL', True)


# Function used to encode response data. Receives a dict and return a string
DEFAULT_ENCODER = DjangoJSONEncoder().encode
ENCODER = getattr(settings, 'CHUNKED_UPLOAD_ENCODER', DEFAULT_ENCODER)


# Content-Type for the response data
DEFAULT_CONTENT_TYPE = 'application/json'
CONTENT_TYPE = getattr(settings, 'CHUNKED_UPLOAD_CONTENT_TYPE',
                       DEFAULT_CONTENT_TYPE)


# CHUNKED_UPLOAD_MIMETYPE is deprecated, but kept for backward compatibility
CONTENT_TYPE = getattr(settings, 'CHUNKED_UPLOAD_MIMETYPE',
                       DEFAULT_CONTENT_TYPE)


# Max amount of data (in bytes) that can be uploaded. `None` means no limit
DEFAULT_MAX_BYTES = None
MAX_BYTES = getattr(settings, 'CHUNKED_UPLOAD_MAX_BYTES', DEFAULT_MAX_BYTES)
