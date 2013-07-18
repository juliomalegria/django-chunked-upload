import re

from django.views.generic import View
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import ChunkedUpload
from .response import Response
from .constants import http_status, COMPLETE, FAILED
from .exceptions import ChunkedUploadError


class ChunkedUploadBaseView(View):
    """
    Base view for the rest of chunked upload views.
    """

    # Has to be a ChunkedUpload subclass
    model = ChunkedUpload

    def get_queryset(self, request):
        """
        Get (and filter) ChunkedUpload queryset.
        By default, user can only continue uploading his own uploads.
        """
        return self.model.objects.filter(user=request.user)

    def get_response_data(self, chunked_upload, request):
        """
        Data for the response. Should return a dictionary-like object.
        Called *only* if POST is successful.
        """
        return {}

    def pre_save(self, chunked_upload, request, new=False):
        """
        Placeholder method for calling before saving an object.
        May be used to set attributes on the object that are implicit
        in either the request, or the url.
        """

    def save(self, chunked_upload, request, new=False):
        """
        Method that calls save(). Overriding may be useful is save() needs
        special args or kwargs.
        """
        chunked_upload.save()

    def post_save(self, chunked_upload, request, new=False):
        """
        Placeholder method for calling after saving an object.
        """

    def _save(self, chunked_upload):
        """
        Wraps save() method.
        """
        new = chunked_upload.id is None
        self.pre_save(chunked_upload, self.request, new=new)
        self.save(chunked_upload, self.request, new=new)
        self.post_save(chunked_upload, self.request, new=new)

    def check_permissions(self, request):
        """
        Grants permission to start/continue an upload based on the request.
        """
        if not request.user.is_authenticated():
            raise ChunkedUploadError(
                status=http_status.HTTP_403_FORBIDDEN,
                detail='Authentication credentials were not provided'
            )

    def _post(self, request, *args, **kwargs):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests.
        """
        try:
            self.check_permissions(request)
            return self._post(request, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)


class ChunkedUploadView(ChunkedUploadBaseView):
    """
    Uploads large files in multiple chunks. Also, has the ability to resume
    if the upload is interrupted.
    """

    field_name = 'file'
    content_range_pattern = re.compile(r'^bytes (?P<start>\d+)-(?P<end>\d+)/')

    def get_extra_attrs(self, request):
        """
        Extra attribute values to be passed to the new ChunkedUpload instance.
        Should return a dictionary-like object.
        """
        return {}

    def create_chunked_upload(self, save=False, **attrs):
        """
        Creates new chunked upload instance. Called if no 'upload_id' is
        found in the POST data.
        """
        chunked_upload = self.model(**attrs)
        # file starts empty
        chunked_upload.file.save(name='', content=ContentFile(''), save=save)
        return chunked_upload

    def is_valid_chunked_upload(self, chunked_upload):
        """
        Check if chunked upload has already expired or is already complete.
        """
        if chunked_upload.expired:
            raise ChunkedUploadError(status=http_status.HTTP_410_GONE,
                                     detail='Upload has expired')
        error_msg = 'Upload has already been marked as "%s"'
        if chunked_upload.status == COMPLETE:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg % 'complete')
        if chunked_upload.status == FAILED:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg % 'failed')

    def get_response_data(self, chunked_upload, request):
        """
        Data for the response. Should return a dictionary-like object.
        """
        return {
            'upload_id': chunked_upload.upload_id,
            'offset': chunked_upload.offset,
            'expires': chunked_upload.expires_on
        }

    def _post(self, request, *args, **kwargs):
        chunk = request.FILES.get(self.field_name)
        if chunk is None:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail='No chunk file was submitted')

        upload_id = request.POST.get('upload_id')
        if upload_id:
            chunked_upload = get_object_or_404(self.get_queryset(request),
                                               upload_id=upload_id)
            self.is_valid_chunked_upload(chunked_upload)
        else:
            attrs = {'user': request.user, 'filename': chunk.name}
            attrs.update(self.get_extra_attrs(request))
            chunked_upload = self.create_chunked_upload(save=False, **attrs)

        content_range = request.META.get('HTTP_CONTENT_RANGE', '')
        match = self.content_range_pattern.match(content_range)
        if not match:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail='Error in request headers')

        start = int(match.group('start'))
        end = int(match.group('end'))
        if chunked_upload.offset != start:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail='Offsets do not match',
                                     offset=chunked_upload.offset)

        chunk_size = end - start + 1
        chunked_upload.append_chunk(chunk, chunk_size=chunk_size, save=False)

        self._save(chunked_upload)

        return Response(self.get_response_data(chunked_upload, request),
                        status=http_status.HTTP_200_OK)


class ChunkedUploadCompleteView(ChunkedUploadBaseView):
    """
    Completes an chunked upload. Method `on_completion` is a placeholder to
    define what to do when upload is complete.
    """

    def on_completion(self, uploaded_file, request):
        """
        Placeholder method to define what to do when upload is complete.
        """

    def is_valid_chunked_upload(self, chunked_upload):
        """
        Check if chunked upload is already complete.
        """
        if chunked_upload.status == COMPLETE:
            error_msg = "Upload has already been marked as complete"
            return ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                      detail=error_msg)

    def md5_check(self, chunked_upload, md5):
        """
        Verify if md5 checksum sent by client matches generated md5.
        """
        if chunked_upload.md5 != md5:
            chunked_upload.status = FAILED
            self._save(chunked_upload)
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail='md5 checksum does not match')

    def _post(self, request, *args, **kwargs):
        upload_id = request.POST.get('upload_id')
        md5 = request.POST.get('md5')
        if not upload_id:
            error_msg = "Both 'upload_id' and 'md5' are required"
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg)

        chunked_upload = get_object_or_404(self.get_queryset(request),
                                           upload_id=upload_id)
        self.is_valid_chunked_upload(chunked_upload)
        self.md5_check(chunked_upload, md5)

        chunked_upload.status = COMPLETE
        chunked_upload.completed_on = timezone.now()
        self._save(chunked_upload)
        self.on_completion(chunked_upload.get_uploaded_file(), request)

        return Response(self.get_response_data(chunked_upload, request),
                        status=http_status.HTTP_200_OK)
