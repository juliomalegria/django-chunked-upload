#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('VERSION.txt', 'r') as v:
    version = v.read().strip()

with open('README.rst', 'r') as r:
    readme = r.read()

download_url = (
    'https://github.com/jerinpetergeorge/django-chunk-upload/tarball/%s'
)


setup(
    name='django-chunk-upload',
    packages=['django_chunk_upload'],
    version=version,
    description=('Upload large files to Django in multiple chunks, with the '
                 'ability to resume if the upload is interrupted.'),
    long_description=readme,
    author='Jerin Peter George',
    author_email='jerinpetergeorge@gmail.com',
    url='https://github.com/jerinpetergeorge/django-chunk-upload',
    download_url=download_url % version,
    install_requires=[],
    license='MIT-Zero'
)
