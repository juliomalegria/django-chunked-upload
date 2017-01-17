from django.contrib import admin

from .models import ChunkedUpload
from .settings import ABSTRACT_MODEL


class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display = ('dataset__upload_id', 'filename', 'user', 'status', 'created_on', 'field_name')
    search_fields = ('filename',)
    list_filter = ('status',)

if not ABSTRACT_MODEL:  # If the model exists
    admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
