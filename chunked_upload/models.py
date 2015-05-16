import time
import os.path
import hashlib
import zlib
import uuid

from django.db import models
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .settings import EXPIRATION_DELTA, UPLOAD_PATH, STORAGE, ABSTRACT_MODEL
from .constants import CHUNKED_UPLOAD_CHOICES, UPLOADING, SUPPORTED_CHUCKSUM_ALGORITHMS

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_upload_id():
    return uuid.uuid4().hex


def generate_filename(instance, filename):
    filename = os.path.join(UPLOAD_PATH, instance.upload_id + '.part')
    return time.strftime(filename)


class ChunkedUpload(models.Model):
    upload_id = models.CharField(max_length=32, unique=True, editable=False,
                                 default=generate_upload_id)
    file = models.FileField(max_length=255, upload_to=generate_filename,
                            storage=STORAGE)
    filename = models.CharField(max_length=255)
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='chunked_uploads')
    offset = models.PositiveIntegerField(default=0)
    created_on = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(choices=CHUNKED_UPLOAD_CHOICES,
                                              default=UPLOADING)
    completed_on = models.DateTimeField(null=True, blank=True)

    @property
    def expires_on(self):
        return self.created_on + EXPIRATION_DELTA

    @property
    def expired(self):
        return self.expires_on <= timezone.now()

    @property
    def md5(self):
        if getattr(self, '_md5', None) is None:
            md5 = hashlib.md5()
            for chunk in self.file.chunks():
                md5.update(chunk)
            self._md5 = md5.hexdigest()
        return self._md5

    @property
    def sha1(self):
        print(self.__dict__)
        print(123)
        if getattr(self, '_sha1', None) is None:
            sha1 = hashlib.sha1()
            for chunk in self.file.chunks():
                sha1.update(chunk)
            self._sha1 = sha1.hexdigest()
        return self._sha1

    @property
    def sha224(self):
        if getattr(self, '_sha224', None) is None:
            sha224 = hashlib.sha224()
            for chunk in self.file.chunks():
                sha224.update(chunk)
            self._sha224 = sha224.hexdigest()
        return self._sha224

    @property
    def sha256(self):
        if getattr(self, '_sha256', None) is None:
            sha256 = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256.update(chunk)
            self._sha256 = sha256.hexdigest()
        return self._sha256

    @property
    def sha384(self):
        if getattr(self, '_sha384', None) is None:
            sha384 = hashlib.sha384()
            for chunk in self.file.chunks():
                sha384.update(chunk)
            self._sha384 = sha384.hexdigest()
        return self._sha384

    @property
    def sha512(self):
        if getattr(self, '_sha512', None) is None:
            sha512 = hashlib.sha512()
            for chunk in self.file.chunks():
                sha512.update(chunk)
            self._sha512 = sha512.hexdigest()
        return self._sha512

    @property
    def sha512(self):
        if getattr(self, '_sha512', None) is None:
            sha512 = hashlib.sha512()
            for chunk in self.file.chunks():
                sha512.update(chunk)
            self._sha512 = sha512.hexdigest()
        return self._sha512

    @property
    def adler32(self):
        if getattr(self, "_adler32", None) is None:
            adler32 = 0
            for chunk in self.file.chunks():
                adler32 = zlib.adler32(chunk, adler32)
            self._adler32 = str(adler32)
        return self._adler32

    @property
    def crc32(self):
        if getattr(self, "_crc32", None) is None:
            crc32 = 0
            for chunk in self.file.chunks():
                crc32 = zlib.crc32(chunk, crc32)
            self._crc32 = str(crc32)
        return self._crc32


    def delete(self, delete_file=True, *args, **kwargs):
        storage, path = self.file.storage, self.file.path
        super(ChunkedUpload, self).delete(*args, **kwargs)
        if delete_file:
            storage.delete(path)

    def __unicode__(self):
        return u'<%s - upload_id: %s - bytes: %s - status: %s>' % (
            self.filename, self.upload_id, self.offset, self.status)

    def close_file(self):
        """
        Bug in django 1.4: FieldFile `close` method is not reaching all the
        way to the actual python file.
        Fix: we had to loop all inner files and close them manually.
        """
        file_ = self.file
        while file_ is not None:
            file_.close()
            file_ = getattr(file_, 'file', None)

    def append_chunk(self, chunk, chunk_size=None, save=True):
        self.close_file()
        self.file.open(mode='ab')  # mode = append+binary
        # We can use .read() safely because chunk is already in memory
        self.file.write(chunk.read())
        if chunk_size is not None:
            self.offset += chunk_size
        elif hasattr(chunk, 'size'):
            self.offset += chunk.size
        else:
            self.offset = self.file.size
        # clear cached checksum
        for checksum_type in SUPPORTED_CHUCKSUM_ALGORITHMS:
            checksum = getattr(self, "_" + checksum_type, None)
            if checksum is not None:
                checksum = None
        if save:
            self.save()
        self.close_file()  # Flush

    def get_uploaded_file(self):
        self.close_file()
        self.file.open(mode='rb')  # mode = read+binary
        return UploadedFile(file=self.file, name=self.filename,
                            size=self.offset)

    class Meta:
        abstract = ABSTRACT_MODEL
