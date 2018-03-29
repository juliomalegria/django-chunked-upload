import tempfile

from django.core.files.storage import FileSystemStorage


class TemporaryFileStorage(FileSystemStorage):
    location = tempfile.gettempdir()