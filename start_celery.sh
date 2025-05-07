#!/bin/bash

# Kill existing Celery worker processes
pkill -f 'celery worker'

# Start Celery worker
celery -A vitigo_pms worker -l INFO --pool=solo
