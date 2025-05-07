from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['vitigoapp.com', 'localhost', '127.0.0.1', '::1', 'yourserverip', 'vitigo-render-hopefull-database-v6z3.onrender.com']
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = []
