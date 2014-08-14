# django-chunked-upload

This simple django app enables users to upload large files to Django in multiple chunks, with the ability to resume if
the upload is interrupted.

This app is intented to work with [JQuery-File-Upload](https://github.com/blueimp/jQuery-File-Upload) by
[Sebastian Tschan](https://blueimp.net/).

## Typical usage

1. An initial POST request is sent to the url linked to `ChunkedUploadView` (or any subclass) with the first chunk of
the file. The key of this chunk can be overriden in the view (class attribute `field_name`). Example:

        {'my_file': <File>}

2. In return, server with response with the `upload_id`, the current `offset` and the when will the upload expire
(`expires`). Example:

        {'upload_id': '5230ec1f59d1485d9d7974b853802e31',
         'offset': 10000,
         'expires': '2013-07-18T17:56:22.186Z'}

3. Repeatedly POST subsequent chunks using the `upload_id` to identify the upload  to the url linked to
`ChunkedUploadView` (or any subclass). Example:

        {'upload_id': '5230ec1f59d1485d9d7974b853802e31',
         'my_file': <File>}


4. Server will continue responding with the `upload_id`, the current `offset` and the expiration date (`expires`).

5. Finally, when upload is completed, a POST request is sent to the url linked to `ChunkedUploadCompleteView`
(or any subclass). This request must include the `upload_id` and the `md5` checksum (hex). Example:

        {'upload_id': '5230ec1f59d1485d9d7974b853802e31',
         'md5': 'fc3ff98e8c6a0d3087d515c0473f8677'}

6. If everything is OK, server will response with status code 200 and the data returned in the method `get_response_data`
(if any).

### Possible error responses:

* User is not authenticated. Server responds 403 (Forbidden).
* Upload has expired. Server responds 410 (Gone).
* `upload_id` does not match any upload. Server responds 404 (Not found).
* No chunk file is found in the indicated key. Server responds 400 (Bad request).
* Request does not contain `Content-Range` header. Server responds 400 (Bad request).
* Size of file exceeds limit (if specified).  Server responds 400 (Bad request).
* Offsets does not match.  Server responds 400 (Bad request).
* `md5` checksums does not match. Server responds 400 (Bad request).

## Settings

Add any of these variables into your project settings to override them.

#### `CHUNKED_UPLOAD_EXPIRATION_DELTA`

* How long after creation the upload will expire.
* Default: `datetime.timedelta(days=1)`

#### `CHUNKED_UPLOAD_PATH`

* Path where uploading files will be stored until completion.
* Default: `'chunked_uploads/%Y/%m/%d'`

#### `CHUNKED_UPLOAD_STORAGE_CLASS`

* Storage system (should be a class).
* Default: `None` (use default storage system)

#### `CHUNKED_UPLOAD_ABSTRACT_MODEL`

* Boolean that defines if the `ChunkedUpload` model will be abstract or not ([what does abstract model mean?](https://docs.djangoproject.com/en/1.4/ref/models/options/#abstract)).
* Default: `True`

#### `CHUNKED_UPLOAD_ENCODER`

* Function used to encode response data. Receives a dict and returns a string.
* Default: `DjangoJSONEncoder().encode`

#### `CHUNKED_UPLOAD_MIMETYPE`

* Mimetype for the response data.
* Default: `'application/json'`

#### `CHUNKED_UPLOAD_MAX_BYTES`

* Max amount of data (in bytes) that can be uploaded. `None` means no limit.
* Default: `None`

## Support

If you find any bug or you want to propose a new feature, please use the [issues tracker](https://github.com/juliomalegria/django-chunked-upload/issues). I'll be happy to help you! :-)
