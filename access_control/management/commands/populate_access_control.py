from django.core.management.base import BaseCommand
from access_control.models import Module, Role, ModulePermission

class Command(BaseCommand):
    help = 'Populate initial modules, roles and permissions for access control'

    def handle(self, *args, **kwargs):
        # Define modules with their attributes
        modules = [
            # Core Management
            {'name': 'dashboard', 'display_name': 'Dashboard', 'url_name': 'dashboard', 'order': 1},
            {'name': 'patient_management', 'display_name': 'Patient Management', 'url_name': 'patient_dashboard', 'order': 2},
            {'name': 'appointment_management', 'display_name': 'Appointments', 'url_name': 'appointment_dashboard', 'order': 3},
            
            # Clinical
            {'name': 'consultation_management', 'display_name': 'Consultations', 'url_name': 'consultation_dashboard', 'order': 10},
            {'name': 'procedure_management', 'display_name': 'Procedures', 'url_name': 'procedure_dashboard', 'order': 11},
            {'name': 'phototherapy_management', 'display_name': 'Phototherapy', 'url_name': 'phototherapy_dashboard', 'order': 12},
            {'name': 'image_management', 'display_name': 'Image Management', 'url_name': 'image_dashboard', 'order': 13},
            {'name': 'lab_management', 'display_name': 'Laboratory', 'url_name': 'lab_dashboard', 'order': 14},
            
            # Pharmacy & Inventory
            {'name': 'pharmacy_management', 'display_name': 'Pharmacy', 'url_name': 'pharmacy_dashboard', 'order': 20},
            {'name': 'stock_management', 'display_name': 'Stock Management', 'url_name': 'stock_dashboard', 'order': 21},
            
            # Administration
            {'name': 'financial_management', 'display_name': 'Finance', 'url_name': 'financial_dashboard', 'order': 30},
            {'name': 'hr_management', 'display_name': 'HR Management', 'url_name': 'hr_dashboard', 'order': 31},
            {'name': 'reporting_and_analytics', 'display_name': 'Reports & Analytics', 'url_name': 'reporting_dashboard', 'order': 32},
            {'name': 'access_control', 'display_name': 'Access Control', 'url_name': 'access_control_dashboard', 'order': 33},
            {'name': 'clinic_management', 'display_name': 'Clinic Management', 'url_name': 'clinic_dashboard', 'order': 34},
            
            # Support & Settings
            {'name': 'help_support', 'display_name': 'Help & Support', 'url_name': 'help_support_dashboard', 'order': 40},
            {'name': 'settings', 'display_name': 'Settings', 'url_name': 'settings_dashboard', 'order': 41},
            
            # Additional Features
            {'name': 'telemedicine_management', 'display_name': 'Telemedicine', 'url_name': 'telemedicine_dashboard', 'order': 50},
            {'name': 'research_management', 'display_name': 'Research', 'url_name': 'research_dashboard', 'order': 51},
            {'name': 'query_management', 'display_name': 'Queries', 'url_name': 'query_dashboard', 'order': 52},
            {'name': 'user_management', 'display_name': 'User Management', 'url_name': 'user_dashboard', 'order': 53},
            {'name': 'notification_management', 'display_name': 'Notification Management', 'url_name': 'notification_dashboard', 'order': 54},
            {'name': 'asset_management', 'display_name': 'Asset Management', 'url_name': 'asset_dashboard', 'order': 55},
            {'name': 'compliance_management', 'display_name': 'Compliance Management', 'url_name': 'compliance_dashboard', 'order': 56},
        ]

        # Define roles with their attributes
        roles = [
            # Administrative Roles
            {'name': 'SUPER_ADMIN', 'display_name': 'Super Administrator', 'template_folder': 'admin'},
            {'name': 'ADMINISTRATOR', 'display_name': 'Administrator', 'template_folder': 'administrator'},
            {'name': 'MANAGER', 'display_name': 'Clinic Manager', 'template_folder': 'admin'},
            
            # Medical Staff
            {'name': 'DOCTOR', 'display_name': 'Doctor', 'template_folder': 'doctor'},
            {'name': 'NURSE', 'display_name': 'Nurse', 'template_folder': 'nurse'},
            {'name': 'MEDICAL_ASSISTANT', 'display_name': 'Medical Assistant', 'template_folder': 'medical'},
            
            # Support Staff
            {'name': 'RECEPTIONIST', 'display_name': 'Receptionist', 'template_folder': 'reception'},
            {'name': 'PHARMACIST', 'display_name': 'Pharmacist', 'template_folder': 'pharmacy'},
            {'name': 'LAB_TECHNICIAN', 'display_name': 'Lab Technician', 'template_folder': 'lab'},
            
            # Specialized Roles
            {'name': 'BILLING_STAFF', 'display_name': 'Billing Staff', 'template_folder': 'billing'},
            {'name': 'INVENTORY_MANAGER', 'display_name': 'Inventory Manager', 'template_folder': 'inventory'},
            {'name': 'HR_STAFF', 'display_name': 'HR Staff', 'template_folder': 'hr'},
            
            # Support Roles
            {'name': 'SUPPORT_MANAGER', 'display_name': 'Support Manager', 'template_folder': 'support'},
            {'name': 'SUPPORT_STAFF', 'display_name': 'Support Staff', 'template_folder': 'support'},

            # Additional Roles
            {'name': 'PATIENT', 'display_name': 'Patient', 'template_folder': 'patient'},
        ]

        # Create Modules
        created_modules = []
        for module_data in modules:
            module, created = Module.objects.get_or_create(
                name=module_data['name'],
                defaults={
                    'display_name': module_data['display_name'],
                    'url_name': module_data['url_name'],
                    'order': module_data['order']
                }
            )
            created_modules.append(module)
            self.stdout.write(
                self.style.SUCCESS(f'{"Created" if created else "Already exists"}: module "{module_data["display_name"]}"')
            )

        # Create Roles and Permissions
        admin_roles = ['SUPER_ADMIN', 'ADMINISTRATOR']
        for role_data in roles:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'display_name': role_data['display_name'],
                    'template_folder': role_data['template_folder']
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f'{"Created" if created else "Already exists"}: role "{role_data["display_name"]}"')
            )

            # Create module permissions for admin roles
            if role.name in admin_roles:
                for module in created_modules:
                    permission, created = ModulePermission.objects.get_or_create(
                        module=module,
                        role=role,
                        defaults={
                            'can_access': True,
                            'can_modify': True,
                            'can_delete': True
                        }
                    )
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created permissions for {role.name} on {module.name}')
                        )

        self.stdout.write(self.style.SUCCESS('Finished populating access control data'))
        
        # Create template directories
        from django.core.management import call_command
        call_command('create_template_directories')