from django.core.management.base import BaseCommand
from access_control.models import Role, Module, ModulePermission

class Command(BaseCommand):
    help = 'Fix patient role permission for dashboard module'

    def handle(self, *args, **options):
        try:
            patient_role = Role.objects.get(name__iexact='PATIENT')
            dashboard_module = Module.objects.get(name='dashboard')
            permission, created = ModulePermission.objects.get_or_create(role=patient_role, module=dashboard_module)
            permission.can_access = True
            permission.can_modify = False
            permission.can_delete = False
            permission.save()
            self.stdout.write(self.style.SUCCESS('Successfully updated patient dashboard module permission'))
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('Patient role does not exist'))
        except Module.DoesNotExist:
            self.stdout.write(self.style.ERROR('Dashboard module does not exist'))
