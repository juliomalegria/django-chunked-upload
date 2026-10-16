"""Characterization tests, run standalone with ``python runtests.py`` from the repo root.

They pin the library's behaviour through its two views, as an HTTP client sees it.
"""
import hashlib
import os
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chunked_upload.constants import COMPLETE, UPLOADING
from chunked_upload.models import ChunkedUpload
from chunked_upload.views import ChunkedUploadCompleteView, ChunkedUploadView

User = get_user_model()


class ChunkedUploadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pw')
        self.client.force_login(self.user)

    def chunk(self, data, content_range=None, upload_id=None, client=None):
        payload = {'file': SimpleUploadedFile('f.bin', data, content_type='application/octet-stream')}
        if upload_id:
            payload['upload_id'] = upload_id
        extra = {'HTTP_CONTENT_RANGE': content_range} if content_range else {}
        return (client or self.client).post(reverse('chunked-upload'), payload, **extra)

    def complete(self, upload_id, md5, client=None):
        return (client or self.client).post(
            reverse('chunked-upload-complete'), {'upload_id': upload_id, 'md5': md5})


class UploadFlowTests(ChunkedUploadTestCase):
    def test_multi_chunk_upload_then_complete(self):
        body = b'0123456789abcdef'
        first = self.chunk(body[:8], 'bytes 0-7/16')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['offset'], 8)
        upload_id = first.json()['upload_id']

        second = self.chunk(body[8:], 'bytes 8-15/16', upload_id=upload_id)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['offset'], 16)

        done = self.complete(upload_id, hashlib.md5(body).hexdigest())
        self.assertEqual(done.status_code, 200)
        upload = ChunkedUpload.objects.get(upload_id=upload_id)
        self.assertEqual(upload.status, COMPLETE)
        self.assertIsNotNone(upload.completed_on)
        self.assertEqual(upload.user, self.user)
        with upload.file.open('rb') as stored:
            self.assertEqual(stored.read(), body)

    def test_headerless_chunk_is_a_whole_file(self):
        response = self.chunk(b'hello')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['offset'], 5)

    def test_resume_continues_from_the_stored_offset(self):
        body = b'0123456789abcdef'
        upload_id = self.chunk(body[:8], 'bytes 0-7/16').json()['upload_id']

        # The client lost the response; the server's offset tells it where to resume.
        stale = self.chunk(body[:8], 'bytes 0-7/16', upload_id=upload_id)
        self.assertEqual(stale.status_code, 400)
        resume_at = stale.json()['offset']
        self.assertEqual(resume_at, 8)

        resumed = self.chunk(body[resume_at:], 'bytes 8-15/16', upload_id=upload_id)
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()['offset'], 16)

    def test_complete_with_matching_md5(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        response = self.complete(upload_id, hashlib.md5(b'hello').hexdigest())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_complete_with_bad_md5(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        response = self.complete(upload_id, 'f' * 32)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'md5 checksum does not match'})
        self.assertEqual(ChunkedUpload.objects.get(upload_id=upload_id).status, UPLOADING)

    def test_complete_requires_upload_id_and_md5(self):
        response = self.client.post(reverse('chunked-upload-complete'), {'upload_id': 'x'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': "Both 'upload_id' and 'md5' are required"})

    def test_complete_without_md5_check_only_needs_upload_id(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        with mock.patch.object(ChunkedUploadCompleteView, 'do_md5_check', False):
            response = self.client.post(reverse('chunked-upload-complete'), {'upload_id': upload_id})
        self.assertEqual(response.status_code, 200)

    def test_on_completion_runs_with_the_uploaded_file(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        with mock.patch.object(ChunkedUploadCompleteView, 'on_completion') as on_completion:
            self.complete(upload_id, hashlib.md5(b'hello').hexdigest())
        on_completion.assert_called_once()
        uploaded_file = on_completion.call_args.args[0]
        self.assertEqual((uploaded_file.name, uploaded_file.size), ('f.bin', 5))

    def test_a_chunk_for_a_complete_upload_is_refused(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        self.complete(upload_id, hashlib.md5(b'hello').hexdigest())

        response = self.chunk(b'more', 'bytes 5-8/9', upload_id=upload_id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'Upload has already been marked as "complete"'})


class RefusalTests(ChunkedUploadTestCase):
    def test_no_chunk_file(self):
        response = self.client.post(reverse('chunked-upload'), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'No chunk file was submitted'})

    def test_offset_mismatch_carries_the_stored_offset(self):
        upload_id = self.chunk(b'A' * 8, 'bytes 0-7/24').json()['upload_id']

        response = self.chunk(b'C' * 8, 'bytes 16-23/24', upload_id=upload_id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'Offsets do not match', 'offset': 8})

    def test_chunk_size_must_match_the_range(self):
        response = self.chunk(b'A' * 4, 'bytes 0-7/16')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': "File size doesn't match headers"})

    def test_expired_upload_is_gone(self):
        upload_id = self.chunk(b'A' * 8, 'bytes 0-7/16').json()['upload_id']
        ChunkedUpload.objects.filter(upload_id=upload_id).update(
            created_on=timezone.now() - timedelta(days=2))

        response = self.chunk(b'B' * 8, 'bytes 8-15/16', upload_id=upload_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json(), {'detail': 'Upload has expired'})

    def test_max_bytes_refuses_a_total_over_the_limit(self):
        with mock.patch.object(ChunkedUploadView, 'max_bytes', 10):
            response = self.chunk(b'A' * 8, 'bytes 0-7/16')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'Size of file exceeds the limit (10 bytes)'})

    def test_max_bytes_allows_a_total_at_the_limit(self):
        with mock.patch.object(ChunkedUploadView, 'max_bytes', 16):
            response = self.chunk(b'A' * 8, 'bytes 0-7/16')
        self.assertEqual(response.status_code, 200)

    def test_fail_if_no_header(self):
        with mock.patch.object(ChunkedUploadView, 'fail_if_no_header', True):
            response = self.chunk(b'hello')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'Error in request headers'})


class PermissionTests(ChunkedUploadTestCase):
    def test_anonymous_chunk_is_forbidden(self):
        self.client.logout()
        response = self.chunk(b'hello')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'detail': 'Authentication credentials were not provided'})
        self.assertFalse(ChunkedUpload.objects.exists())

    def test_anonymous_complete_is_forbidden(self):
        self.client.logout()
        response = self.complete('x' * 32, 'f' * 32)
        self.assertEqual(response.status_code, 403)

    def test_another_users_upload_is_not_found(self):
        upload_id = self.chunk(b'A' * 8, 'bytes 0-7/16').json()['upload_id']
        bob = User.objects.create_user('bob', password='pw')
        self.client.force_login(bob)

        chunk = self.chunk(b'B' * 8, 'bytes 8-15/16', upload_id=upload_id)
        complete = self.complete(upload_id, 'f' * 32)

        self.assertEqual(chunk.status_code, 404)
        self.assertEqual(complete.status_code, 404)
        self.assertEqual(ChunkedUpload.objects.get(upload_id=upload_id).offset, 8)


class DeleteExpiredUploadsTests(ChunkedUploadTestCase):
    def test_deletes_only_expired_uploads_and_their_files(self):
        old_id = self.chunk(b'A' * 8, 'bytes 0-7/16').json()['upload_id']
        fresh_id = self.chunk(b'B' * 8, 'bytes 0-7/16').json()['upload_id']
        old = ChunkedUpload.objects.get(upload_id=old_id)
        old_path = old.file.path
        ChunkedUpload.objects.filter(pk=old.pk).update(created_on=timezone.now() - timedelta(days=2))

        out = StringIO()
        with mock.patch('sys.stdout', out):
            call_command('delete_expired_uploads')

        self.assertFalse(ChunkedUpload.objects.filter(upload_id=old_id).exists())
        self.assertTrue(ChunkedUpload.objects.filter(upload_id=fresh_id).exists())
        self.assertFalse(os.path.exists(old_path))
        self.assertIn('0 complete uploads were deleted.', out.getvalue())
        self.assertIn('1 incomplete uploads were deleted.', out.getvalue())


class RecompletionTests(ChunkedUploadTestCase):
    def test_completing_a_complete_upload_is_refused(self):
        upload_id = self.chunk(b'hello').json()['upload_id']
        md5 = hashlib.md5(b'hello').hexdigest()
        self.assertEqual(self.complete(upload_id, md5).status_code, 200)

        with mock.patch.object(ChunkedUploadCompleteView, 'on_completion') as on_completion:
            response = self.complete(upload_id, md5)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'Upload has already been marked as complete'})
        on_completion.assert_not_called()

    def test_completing_an_uploading_session_runs_on_completion_once(self):
        upload_id = self.chunk(b'hello').json()['upload_id']

        with mock.patch.object(ChunkedUploadCompleteView, 'on_completion') as on_completion:
            response = self.complete(upload_id, hashlib.md5(b'hello').hexdigest())

        self.assertEqual(response.status_code, 200)
        on_completion.assert_called_once()
