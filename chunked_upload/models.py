import time
import os.path
import hashlib
import uuid

from django.db import models
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .settings import EXPIRATION_DELTA, UPLOAD_PATH, STORAGE, ABSTRACT_MODEL
from .constants import CHUNKED_UPLOAD_CHOICES, UPLOADING

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_upload_id():
	return uuid.uuid4().hex


def generate_filename(instance, filename):
	filename = os.path.join(UPLOAD_PATH, instance.dataset.upload_id + '.part')
	return time.strftime(filename)


class Dataset(models.Model):
	'''
	Dataset handles the upload_id, which was originally saved directly in :model:`chunked_upload.ChunkedUpload`. But because multiple file
	uploads have to work too, Dataset saves the upload_id for all files in one upload to prevent errors.
	'''
	upload_id = models.CharField(max_length=32, unique=True, editable=False,
								 default=generate_upload_id)

	def __str__(self):
		return self.upload_id


class BaseChunkedUpload(models.Model):
	"""
	Base chunked upload model. This model is abstract (doesn't create a table
	in the database).
	Inherit from this model to implement your own.
	"""

	dataset = models.ForeignKey(Dataset)
	file = models.FileField(max_length=255, upload_to=generate_filename,
							storage=STORAGE)
	filename = models.CharField(max_length=255)
	offset = models.BigIntegerField(default=0)
	created_on = models.DateTimeField(auto_now_add=True)
	status = models.PositiveSmallIntegerField(choices=CHUNKED_UPLOAD_CHOICES,
											  default=UPLOADING)
	completed_on = models.DateTimeField(null=True, blank=True)
	field_name = models.CharField(max_length=255)

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

	def delete(self, delete_file=True, *args, **kwargs):
		if self.file:
			storage, path = self.file.storage, self.file.path
		super(BaseChunkedUpload, self).delete(*args, **kwargs)
		if self.file and delete_file:
			storage.delete(path)

	def __unicode__(self):
		return u'<%s - upload_id: %s - bytes: %s - status: %s>' % (
			self.filename, self.dataset.upload_id, self.offset, self.status)

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
		self._md5 = None  # Clear cached md5
		if save:
			self.save()
		self.close_file()  # Flush

	def get_uploaded_file(self):
		self.close_file()
		self.file.open(mode='rb')  # mode = read+binary
		return UploadedFile(file=self.file, name=self.filename,
							size=self.offset)

	class Meta:
		abstract = True


class ChunkedUpload(BaseChunkedUpload):
	"""
	Default chunked upload model.
	It handles the chunked uploaded files, saves them and validates correct saving through md5sum and offset.
	It also gives information about the upload status.
	"""
	pass
