from .settings import *

DEBUG = False

ALLOWED_HOSTS = [
    "gestemg.alwaysdata.net",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gestemg_bd_emg",
        "USER": "gestemg",
        "PASSWORD": "Abdoul@alwaysdata1995",
        "HOST": "postgresql-gestemg.alwaysdata.net",
        "PORT": "5432",
    }
}