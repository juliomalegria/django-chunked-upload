"""URLconf for the standalone test suite: the two views, unmodified."""
from django.urls import path

from chunked_upload.views import ChunkedUploadCompleteView, ChunkedUploadView

urlpatterns = [
    path('upload/', ChunkedUploadView.as_view(), name='chunked-upload'),
    path('upload/complete/', ChunkedUploadCompleteView.as_view(), name='chunked-upload-complete'),
]
