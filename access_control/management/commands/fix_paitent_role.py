from django.core.management.base import BaseCommand
from access_control.models import Role, Module, ModulePermission

class Command(BaseCommand):
    help = 'Fix patient role template_folder and permissions for appointment_management module'

    def handle(self, *args, **options):
        try:
            patient_role = Role.objects.get(name__iexact='PATIENT')
            self.stdout.write(f"Current template_folder for patient role: {patient_role.template_folder}")
            patient_role.template_folder = 'patient'
            patient_role.save()
            self.stdout.write("Updated template_folder for patient role to 'patient'")

            appointment_module = Module.objects.get(name='appointment_management')
            permission, created = ModulePermission.objects.get_or_create(role=patient_role, module=appointment_module)
            permission.can_access = True
            permission.can_modify = False
            permission.can_delete = False
            permission.save()
            self.stdout.write("Ensured patient role has access to appointment_management module")

            self.stdout.write(self.style.SUCCESS("Patient role fixes applied successfully."))

        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR("Patient role does not exist. Please create it first."))
        except Module.DoesNotExist:
            self.stdout.write(self.style.ERROR("Module 'appointment_management' does not exist."))
