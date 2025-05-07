import logging
import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from access_control.models import Role
from clinic_management.models import (
    VisitStatus, ClinicVisit, VisitStatusLog,
    ClinicChecklist, ChecklistItem, VisitChecklist,
    VisitChecklistItem
)

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with sample clinic data'

    def create_admin_user(self):
        """Create an admin user for references"""
        try:
            admin_role, _ = Role.objects.get_or_create(
                name='ADMIN',
                defaults={'display_name': 'Administrator', 'template_folder': 'admin'}
            )
            
            admin_user, created = User.objects.get_or_create(
                email='admin@example.com',
                defaults={
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'role': admin_role,
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                logger.info('Created admin user')
            return admin_user
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            raise

    def create_sample_users(self):
        """Create sample users if they don't exist"""
        try:
            # Create admin user first
            admin_user = self.create_admin_user()
            
            # Get or create roles
            patient_role, _ = Role.objects.get_or_create(
                name='PATIENT',
                defaults={'display_name': 'Patient', 'template_folder': 'patient'}
            )

            # Create sample patients with more details
            patients = []
            for i in range(1, 11):
                try:
                    email = f'patient{i}@example.com'
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'first_name': f'Patient{i}',
                            'last_name': f'Test',
                            'role': patient_role,
                            'is_active': True,
                            'gender': random.choice(['M', 'F']),
                            'country_code': '+91',
                            'phone_number': f'98765{str(i).zfill(5)}'
                        }
                    )
                    if created:
                        user.set_password('password123')
                        user.save()
                        logger.info(f'Created patient user: {email}')
                    patients.append(user)
                except Exception as e:
                    logger.error(f'Error creating patient {i}: {str(e)}')

            return admin_user, patients
        except Exception as e:
            logger.error(f'Error in create_sample_users: {str(e)}')
            return None, []

    def create_visit_statuses(self):
        """Create sample visit statuses"""
        statuses = [
            {'name': 'REGISTERED', 'display_name': 'Registered', 'order': 1},
            {'name': 'WAITING', 'display_name': 'Waiting', 'order': 2},
            {'name': 'IN_PROGRESS', 'display_name': 'In Progress', 'order': 3},
            {'name': 'COMPLETED', 'display_name': 'Completed', 'is_terminal_state': True, 'order': 4},
            {'name': 'CANCELLED', 'display_name': 'Cancelled', 'is_terminal_state': True, 'order': 5},
        ]

        created_statuses = []
        for status_data in statuses:
            try:
                status, created = VisitStatus.objects.get_or_create(
                    name=status_data['name'],
                    defaults=status_data
                )
                created_statuses.append(status)
                if created:
                    logger.info(f'Created visit status: {status.name}')
            except Exception as e:
                logger.error(f'Error creating visit status {status_data["name"]}: {str(e)}')

        return created_statuses

    def create_checklists(self):
        """Create sample checklists and items"""
        checklists_data = [
            {
                'name': 'Registration Checklist',
                'items': [
                    'Verify patient ID',
                    'Check appointment details',
                    'Update contact information',
                ]
            },
            {
                'name': 'Pre-consultation Checklist',
                'items': [
                    'Check vital signs',
                    'Record symptoms',
                    'Review medical history',
                ]
            }
        ]

        created_checklists = []
        for checklist_data in checklists_data:
            try:
                checklist, created = ClinicChecklist.objects.get_or_create(
                    name=checklist_data['name'],
                    defaults={'is_active': True}
                )
                if created:
                    logger.info(f'Created checklist: {checklist.name}')

                for i, item_desc in enumerate(checklist_data['items'], 1):
                    item, item_created = ChecklistItem.objects.get_or_create(
                        checklist=checklist,
                        description=item_desc,
                        defaults={'order': i}
                    )
                    if item_created:
                        logger.info(f'Created checklist item: {item.description}')

                created_checklists.append(checklist)
            except Exception as e:
                logger.error(f'Error creating checklist {checklist_data["name"]}: {str(e)}')

        return created_checklists

    def create_clinic_visits(self, admin_user, patients, statuses, checklists):
        """Create sample clinic visits with status logs and checklists"""
        try:
            for patient in patients:
                # Create 1-3 visits per patient
                for _ in range(random.randint(1, 3)):
                    visit_date = timezone.now() - timedelta(days=random.randint(0, 30))
                    
                    with transaction.atomic():
                        # Create visit with all required fields
                        visit = ClinicVisit.objects.create(
                            patient=patient,
                            visit_date=visit_date,
                            current_status=random.choice(statuses),
                            priority=random.choice(['A', 'B', 'C']),
                            created_by=admin_user,  # Set created_by
                            notes=f"Sample visit for {patient.get_full_name()}"
                        )
                        logger.info(f'Created clinic visit: {visit.visit_number}')

                        # Create status logs with created_by
                        for status in random.sample(list(statuses), random.randint(1, 3)):
                            VisitStatusLog.objects.create(
                                visit=visit,
                                status=status,
                                timestamp=visit_date + timedelta(hours=random.randint(0, 8)),
                                changed_by=admin_user,  # Set changed_by
                                notes=f"Status changed to {status.display_name}"
                            )

                        # Create visit checklists with completed_by
                        for checklist in checklists:
                            visit_checklist = VisitChecklist.objects.create(
                                visit=visit,
                                checklist=checklist,
                                completed_by=admin_user,  # Set completed_by
                                completed_at=visit_date + timedelta(hours=random.randint(0, 4)),
                                notes=f"Checklist for {checklist.name}"
                            )

                            # Create checklist items with completed_by
                            for item in checklist.items.all():
                                VisitChecklistItem.objects.create(
                                    visit_checklist=visit_checklist,
                                    checklist_item=item,
                                    is_completed=random.choice([True, False]),
                                    completed_by=admin_user,  # Set completed_by
                                    completed_at=visit_date + timedelta(hours=random.randint(0, 4)),
                                    notes=f"Item completion status for {item.description}"
                                )

        except Exception as e:
            logger.error(f'Error creating clinic visits: {str(e)}')

    def handle(self, *args, **kwargs):
        try:
            logger.info('Starting clinic data population...')
            
            # Create basic data
            admin_user, patients = self.create_sample_users()
            if not admin_user:
                raise Exception("Failed to create admin user")
                
            statuses = self.create_visit_statuses()
            checklists = self.create_checklists()

            # Create visits and related data
            self.create_clinic_visits(admin_user, patients, statuses, checklists)

            logger.info('Successfully completed clinic data population')
            self.stdout.write(self.style.SUCCESS('Successfully populated clinic data'))

        except Exception as e:
            logger.error(f'Fatal error in populate_clinic_data: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
