import os
from django.core.management.base import BaseCommand
from django.conf import settings
from access_control.models import Role, Module

class Command(BaseCommand):
    help = 'Create template directory structure based on roles and modules'

    def handle(self, *args, **kwargs):
        # Get the base template directory from settings
        template_dir = os.path.join(settings.BASE_DIR, 'templates')
        
        # Ensure base template directory exists
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
            self.stdout.write(self.style.SUCCESS(f'Created base template directory: {template_dir}'))

        # Get all roles and modules
        roles = Role.objects.all()
        modules = Module.objects.filter(is_active=True)

        # Create directories for each role
        for role in roles:
            role_dir = os.path.join(template_dir, role.template_folder)
            
            # Create role directory if it doesn't exist
            if not os.path.exists(role_dir):
                os.makedirs(role_dir)
                self.stdout.write(self.style.SUCCESS(f'Created role directory: {role_dir}'))
            else:
                self.stdout.write(self.style.WARNING(f'Role directory already exists: {role_dir}'))

            # Create module subdirectories for each role
            for module in modules:
                module_dir = os.path.join(role_dir, module.name)
                
                # Create module directory if it doesn't exist
                if not os.path.exists(module_dir):
                    os.makedirs(module_dir)
                    self.stdout.write(
                        self.style.SUCCESS(f'Created module directory: {module_dir}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Module directory already exists: {module_dir}')
                    )