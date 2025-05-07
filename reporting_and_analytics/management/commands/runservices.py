from django.core.management.base import BaseCommand
import subprocess
import os

class Command(BaseCommand):
    help = 'Start development server with Redis and Celery worker'

    def handle(self, *args, **options):
        try:
            # Start Redis if not running
            self.stdout.write('Starting Redis...')
            subprocess.Popen(['brew', 'services', 'start', 'redis'])

            # Start Celery worker
            self.stdout.write('Starting Celery worker...')
            celery_cmd = 'celery -A vitigo_pms worker -l INFO --pool=solo'
            celery_process = subprocess.Popen(celery_cmd.split())

            # Start Django development server
            self.stdout.write('Starting Django development server...')
            self.stdout.write('Visit http://127.0.0.1:8000/')
            os.system('python manage.py runserver')

        except KeyboardInterrupt:
            self.stdout.write('Stopping all services...')
            celery_process.terminate()
            subprocess.run(['brew', 'services', 'stop', 'redis'])
