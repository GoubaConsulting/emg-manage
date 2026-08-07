from .settings import *

DEBUG = True

ALLOWED_HOSTS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bd_emg",
        "USER": "postgres",
        "PASSWORD": "Abdoul",
        "HOST": "localhost",
        "PORT": "5432",
    }
}