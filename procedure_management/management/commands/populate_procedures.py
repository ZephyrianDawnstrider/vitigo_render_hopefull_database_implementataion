import logging
from datetime import datetime, timedelta
from random import choice, randint, uniform
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from faker import Faker

from procedure_management.models import (
    ProcedureCategory, ProcedureType, ProcedurePrerequisite,
    ProcedureInstruction, Procedure, ConsentForm, 
    ProcedureChecklistTemplate, ChecklistItem, ProcedureMedia,
    CompletedChecklistItem, ProcedureChecklist
)
from appointment_management.models import Appointment

logger = logging.getLogger(__name__)
fake = Faker()
User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with sample procedure data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--procedures',
            type=int,
            default=50,
            help='Number of procedures to create'
        )

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write('Starting procedure data population...')
            logger.info('Beginning procedure data population')

            with transaction.atomic():
                # Clear existing data
                self.clear_existing_data()
                
                # Create base data
                categories = self.create_categories()
                procedure_types = self.create_procedure_types(categories)
                self.create_prerequisites(procedure_types)
                self.create_instructions(procedure_types)
                checklist_templates = self.create_checklist_templates(procedure_types)
                
                # Create procedures and related data
                num_procedures = kwargs['procedures']
                self.create_procedures(num_procedures, procedure_types, checklist_templates)

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully populated procedure data with {num_procedures} procedures'
                ))
                logger.info(f'Procedure data population completed with {num_procedures} procedures')

        except Exception as e:
            logger.error(f'Error populating procedure data: {str(e)}', exc_info=True)
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def clear_existing_data(self):
        """Clear all existing procedure-related data"""
        try:
            logger.info('Clearing existing procedure data')
            models_to_clear = [
                ProcedureMedia,
                CompletedChecklistItem,  # Add this
                ProcedureChecklist,
                ConsentForm,
                Procedure,
                ChecklistItem,
                ProcedureChecklistTemplate,
                ProcedureInstruction,
                ProcedurePrerequisite,
                ProcedureType,
                ProcedureCategory
            ]
            for model in models_to_clear:
                model.objects.all().delete()
            logger.info('Existing procedure data cleared successfully')
        except Exception as e:
            logger.error(f'Error clearing existing data: {str(e)}')
            raise

    def create_categories(self):
        """Create procedure categories"""
        try:
            categories = [
                ('Dermatological', 'Skin-related medical procedures'),
                ('Surgical', 'Various surgical procedures'),
                ('Diagnostic', 'Diagnostic medical procedures'),
                ('Therapeutic', 'Treatment-focused procedures'),
                ('Preventive', 'Preventive medical procedures')
            ]
            
            created_categories = []
            for name, desc in categories:
                category = ProcedureCategory.objects.create(
                    name=name,
                    description=desc,
                    is_active=True
                )
                created_categories.append(category)
            
            logger.info(f'Created {len(created_categories)} procedure categories')
            return created_categories
        except Exception as e:
            logger.error(f'Error creating categories: {str(e)}')
            raise

    def create_procedure_types(self, categories):
        """Create procedure types for each category"""
        try:
            procedure_types = []
            for category in categories:
                for i in range(3):  # 3 types per category
                    name = f"{category.name} Procedure {i+1}"
                    procedure_type = ProcedureType.objects.create(
                        category=category,
                        name=name,
                        code=f"{category.name[:3].upper()}{i+1}",
                        description=fake.text(max_nb_chars=200),
                        duration_minutes=choice([30, 45, 60, 90, 120]),
                        base_cost=round(uniform(100.0, 1000.0), 2),
                        priority=choice(['A', 'B', 'C']),
                        requires_consent=choice([True, False]),
                        requires_fasting=choice([True, False]),
                        recovery_time_minutes=randint(30, 240),
                        risk_level=choice(['LOW', 'MODERATE', 'HIGH']),
                        is_active=True
                    )
                    procedure_types.append(procedure_type)
            
            logger.info(f'Created {len(procedure_types)} procedure types')
            return procedure_types
        except Exception as e:
            logger.error(f'Error creating procedure types: {str(e)}')
            raise

    def create_prerequisites(self, procedure_types):
        """Create prerequisites for procedure types"""
        try:
            prerequisites = []
            for proc_type in procedure_types:
                for i in range(randint(2, 4)):
                    prerequisite = ProcedurePrerequisite.objects.create(
                        procedure_type=proc_type,
                        name=f"Prerequisite {i+1}",
                        description=fake.text(max_nb_chars=100),
                        is_mandatory=choice([True, False]),
                        order=i
                    )
                    prerequisites.append(prerequisite)
            
            logger.info(f'Created {len(prerequisites)} prerequisites')
        except Exception as e:
            logger.error(f'Error creating prerequisites: {str(e)}')
            raise

    def create_instructions(self, procedure_types):
        """Create instructions for procedure types"""
        try:
            instructions = []
            for proc_type in procedure_types:
                for inst_type in ['PRE', 'POST']:
                    for i in range(randint(2, 4)):
                        instruction = ProcedureInstruction.objects.create(
                            procedure_type=proc_type,
                            instruction_type=inst_type,
                            title=f"{inst_type} Instruction {i+1}",
                            description=fake.text(max_nb_chars=150),
                            order=i,
                            is_active=True
                        )
                        instructions.append(instruction)
            
            logger.info(f'Created {len(instructions)} instructions')
        except Exception as e:
            logger.error(f'Error creating instructions: {str(e)}')
            raise

    def create_checklist_templates(self, procedure_types):
        """Create checklist templates and items"""
        try:
            templates = []
            for proc_type in procedure_types:
                template = ProcedureChecklistTemplate.objects.create(
                    procedure_type=proc_type,
                    name=f"Checklist for {proc_type.name}",
                    description=f"Standard checklist for {proc_type.name}",
                    is_active=True
                )
                
                # Create checklist items
                for i in range(randint(3, 6)):
                    ChecklistItem.objects.create(
                        template=template,
                        description=f"Check item {i+1}",
                        is_mandatory=choice([True, False]),
                        order=i
                    )
                
                templates.append(template)
            
            logger.info(f'Created {len(templates)} checklist templates')
            return templates
        except Exception as e:
            logger.error(f'Error creating checklist templates: {str(e)}')
            raise

    def create_procedures(self, num_procedures, procedure_types, checklist_templates):
        """Create procedures and related data"""
        try:
            procedures = []
            doctors = User.objects.filter(role__name='DOCTOR')
            patients = User.objects.filter(role__name='PATIENT')
            staff = User.objects.filter(role__name__in=['NURSE', 'STAFF'])

            if not (doctors.exists() and patients.exists()):
                raise ValueError("No doctors or patients found in the database")

            for _ in range(num_procedures):
                # Create procedure
                procedure = Procedure.objects.create(
                    procedure_type=choice(procedure_types),
                    patient=choice(patients),
                    appointment=self.create_appointment(),
                    primary_doctor=choice(doctors),
                    scheduled_date=fake.date_between(
                        start_date='-30d',
                        end_date='+30d'
                    ),
                    scheduled_time=fake.time(),
                    status=choice([s[0] for s in Procedure.STATUS_CHOICES]),
                    notes=fake.text(max_nb_chars=200),
                    final_cost=round(uniform(100.0, 2000.0), 2),
                    payment_status=choice(['PENDING', 'PARTIAL', 'COMPLETED']),
                    created_by=choice(doctors)
                )

                # Add assisting staff
                procedure.assisting_staff.add(*[choice(staff) for _ in range(randint(1, 3))])

                # Create consent form
                if procedure.procedure_type.requires_consent:
                    self.create_consent_form(procedure)

                # Create procedure checklist
                self.create_procedure_checklist(procedure)

                # Create media files
                self.create_media_files(procedure)

                procedures.append(procedure)

            logger.info(f'Created {len(procedures)} procedures with related data')
        except Exception as e:
            logger.error(f'Error creating procedures: {str(e)}')
            raise

    def create_appointment(self):
        """Create a dummy appointment for the procedure"""
        try:
            # Get random doctor and patient
            doctor = User.objects.filter(role__name='DOCTOR').order_by('?').first()
            patient = User.objects.filter(role__name='PATIENT').order_by('?').first()
            
            if not doctor or not patient:
                raise ValueError("No doctors or patients found in database")

            appointment_date = fake.date_between(start_date='-30d', end_date='+30d')
            
            return Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_type='PROCEDURE',  # This is important for procedures
                date=appointment_date,
                status='SCHEDULED',
                priority=choice(['A', 'B', 'C']),
                notes=fake.text(max_nb_chars=100)
            )
        except Exception as e:
            logger.error(f'Error creating appointment: {str(e)}')
            raise

    def create_consent_form(self, procedure):
        """Create consent form for a procedure"""
        try:
            ConsentForm.objects.create(
                procedure=procedure,
                signed_by_patient=choice([True, False]),
                signed_datetime=timezone.now() if choice([True, False]) else None,
                witness_name=fake.name() if choice([True, False]) else '',
                notes=fake.text(max_nb_chars=100) if choice([True, False]) else ''
            )
        except Exception as e:
            logger.error(f'Error creating consent form: {str(e)}')
            raise

    def create_procedure_checklist(self, procedure):
        """Create checklist for a procedure with completed items"""
        try:
            template = procedure.procedure_type.checklist_templates.first()
            if template:
                # Create the procedure checklist
                checklist = ProcedureChecklist.objects.create(
                    procedure=procedure,
                    template=template,
                    completed_by=procedure.created_by,
                    notes=fake.text(max_nb_chars=100) if choice([True, False]) else ''
                )

                # Create completed checklist items
                for item in template.items.all():
                    is_completed = choice([True, False])
                    completed_item = CompletedChecklistItem.objects.create(
                        checklist=checklist,
                        item=item,
                        is_completed=is_completed,
                        completed_by=procedure.created_by if is_completed else None,
                        completed_at=timezone.now() if is_completed else None,
                        notes=fake.text(max_nb_chars=50) if is_completed else ''
                    )

                logger.info(f'Created checklist with {template.items.count()} items for procedure {procedure.pk}')
        except Exception as e:
            logger.error(f'Error creating procedure checklist: {str(e)}')
            raise

    def create_media_files(self, procedure):
        """Create sample media files for a procedure"""
        try:
            for i in range(randint(0, 3)):
                ProcedureMedia.objects.create(
                    procedure=procedure,
                    title=f"Media File {i+1}",
                    description=fake.text(max_nb_chars=100),
                    file_type=choice(['IMAGE', 'DOCUMENT', 'OTHER']),
                    is_private=choice([True, False]),
                    uploaded_by=procedure.created_by
                )
        except Exception as e:
            logger.error(f'Error creating media files: {str(e)}')
            raise
