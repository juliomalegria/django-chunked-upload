# -*- coding: UTF-8 -*-

# Import from the Standard Library
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='django-chunked-upload',
    packages=['chunked_upload'],
)
