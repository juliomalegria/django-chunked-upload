from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import ugettext as _

from .settings import EXPIRATION_DELTA
from .models import ChunkedUpload
from .constants import UPLOADING, COMPLETE, FAILED

prompt_msg = _(u'Do you want to delete {obj}?')


class Command(BaseCommand):

    # Has to be a ChunkedUpload subclass
    model = ChunkedUpload

    help = 'Deletes chunked uploads that have already expired.'

    option_list = BaseCommand.option_list + (
        make_option('--interactive',
                    action='store_true',
                    dest='interactive',
                    default=False,
                    help='Prompt confirmation before each deletion.'),
    )

    def handle(self, *args, **options):
        interactive = options.get('interactive')

        count = {UPLOADING: 0, COMPLETE: 0, FAILED: 0}
        qs = self.model.objects.all()
        qs = qs.filter(created_on__gte=(timezone.now() - EXPIRATION_DELTA))

        for chunked_upload in qs:
            if interactive:
                prompt = prompt_msg.format(obj=chunked_upload) + u' (y/n): '
                answer = raw_input(prompt).lower()
                while answer not in ('y', 'n'):
                    answer = raw_input(prompt).lower()
                if answer == 'n':
                    continue

            count[chunked_upload.status] += 1
            # Deleting objects individually to call delete method explicitly
            chunked_upload.delete()

        print '%i complete uploads were deleted.' % count[COMPLETE]
        print '%i incomplete uploads were deleted.' % count[UPLOADING]
        print '%i failed uploads were deleted.' % count[FAILED]
