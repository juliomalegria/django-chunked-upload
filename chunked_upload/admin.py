from django.contrib import admin
from .models import ChunkedUpload



class ChunkedUploadAdmin(admin.ModelAdmin):
    list_display = ('upload_id', 'file', 'filename', 'user', 'offset',
                    'created_on', 'status', 'completed_on')


admin.site.register(ChunkedUpload, ChunkedUploadAdmin)
