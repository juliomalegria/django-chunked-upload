from django.contrib import admin

from .models import ChunkedUpload


class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display = ('dataset', 'filename', 'status', 'created_on', 'field_name')
    search_fields = ('filename',)
    list_filter = ('status',)

admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
