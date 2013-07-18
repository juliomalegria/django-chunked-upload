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
        raise ImportError('Dude! what Django version are you using?')


# How long after creation the upload will expire
DEFAULT_EXPIRATION_DELTA = timedelta(days=1)
EXPIRATION_DELTA = getattr(settings, 'CHUNKED_UPLOAD_EXPIRATION_DELTA',
                           DEFAULT_EXPIRATION_DELTA)


# Path where uploading files will be stored until completion
DEFAULT_UPLOAD_PATH = 'chunked_uploads/%Y/%m/%d'
UPLOAD_PATH = getattr(settings, 'CHUNKED_UPLOAD_PATH', DEFAULT_UPLOAD_PATH)


# Storage system
STORAGE = getattr(settings, 'CHUNKED_UPLOAD_STORAGE_CLASS', lambda: None)()


# Boolean that defines if the ChunkedUpload model is abstract or not
ABSTRACT_MODEL = getattr(settings, 'CHUNKED_UPLOAD_ABSTRACT_MODEL', True)


# Function used to encode response data. Receives a dict and return a string
DEFAULT_ENCODER = DjangoJSONEncoder().encode
ENCODER = getattr(settings, 'CHUNKED_UPLOAD_ENCODER', DEFAULT_ENCODER)


# Mimetype for the response data
DEFAULT_MIMETYPE = 'application/json'
MIMETYPE = getattr(settings, 'CHUNKED_UPLOAD_MIMETYPE', DEFAULT_MIMETYPE)
