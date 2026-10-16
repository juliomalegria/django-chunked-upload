#!/usr/bin/env python
"""Run the django-chunked-upload test suite with no project and no Docker.

    python runtests.py [test labels...]

Requires Django to be importable (``pip install "Django>=4.2"``).
"""
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def main(labels):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
    django.setup()
    runner_class = get_runner(settings)
    failures = runner_class(verbosity=1, interactive=False).run_tests(labels or ['chunked_upload'])
    sys.exit(bool(failures))


if __name__ == '__main__':
    main(sys.argv[1:])
