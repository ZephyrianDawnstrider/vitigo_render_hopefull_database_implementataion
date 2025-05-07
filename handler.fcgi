import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vitigo_pms.settings'

from django.core.wsgi import get_wsgi_application
from wfastcgi import WSGIServer

WSGIServer(get_wsgi_application()).run()
