import os


SECRET_KEY = "9888d58d-d6fd-46cb-9f98-60d372463ad7"

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': ':memory:',
  }
}
