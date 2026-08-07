"""
WSGI config for emg_manage project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv(
        "DJANGO_SETTINGS_MODULE",
        "emg_manage.settings_production"
    )
)

application = get_wsgi_application()
