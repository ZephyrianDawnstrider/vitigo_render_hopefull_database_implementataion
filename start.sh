#!/bin/bash
# Start Gunicorn processes
gunicorn vitigo_pms.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120

# Start Celery worker in background if needed
# celery -A vitigo_pms worker -l INFO --pool=solo &
