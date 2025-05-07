from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import logging
import faker

from consultation_management.models import (
    Consultation, DoctorPrivateNotes, PrescriptionTemplate, TemplateItem,
    Prescription, PrescriptionItem, TreatmentPlan, TreatmentPlanItem,
    StaffInstruction, ConsultationAttachment
)
from pharmacy_management.models import Medication
from stock_management.models import StockItem

logger = logging.getLogger(__name__)
fake = faker.Faker()
User = get_user_model()

MEDICAL_PROCEDURES = [
    "Phototherapy Session",
    "Skin Biopsy",
    "Melanin Assessment",
    "UV Light Treatment",
    "Patch Testing",
    "Microscopic Examination",
    "Vitiligo Surgery",
    "Melanocyte Transplantation",
    "Blister Grafting",
    "Dermabrasion",
    "Skin Grafting",
    "PUVA Therapy"
]

MEDICAL_CONDITIONS = [
    "Focal Vitiligo",
    "Segmental Vitiligo",
    "Non-segmental Vitiligo",
    "Acrofacial Vitiligo",
    "Universal Vitiligo",
    "Mixed Vitiligo",
    "Inflammatory Vitiligo",
    "Trichrome Vitiligo"
]

class Command(BaseCommand):
    help = 'Populates the database with sample consultation data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consultations',
            type=int,
            default=50,
            help='Number of consultations to create'
        )

    def get_random_users(self, role_name, count=1):
        users = User.objects.filter(role__name=role_name)
        return random.sample(list(users), min(count, len(users)))

    def create_prescription_template(self, doctor):
        try:
            template = PrescriptionTemplate.objects.create(
                name=f"Template for {random.choice(MEDICAL_CONDITIONS)}",
                doctor=doctor,
                description=fake.text(max_nb_chars=200),
                is_global=random.choice([True, False])
            )

            medications = Medication.objects.all()
            if medications.exists():
                for i in range(random.randint(1, 5)):
                    TemplateItem.objects.create(
                        template=template,
                        medication=random.choice(medications),
                        dosage=f"{random.randint(1, 3)} tablet(s)",
                        frequency=f"{random.randint(1, 3)} times daily",
                        duration=f"{random.randint(1, 30)} days",
                        instructions=fake.text(max_nb_chars=100),
                        order=i
                    )
            return template
        except Exception as e:
            logger.error(f"Error creating prescription template: {str(e)}")
            return None

    def create_consultation_data(self):
        try:
            doctor = random.choice(self.get_random_users('DOCTOR'))
            patient = random.choice(self.get_random_users('PATIENT'))
            
            scheduled_date = timezone.now() + timedelta(
                days=random.randint(-30, 30),
                hours=random.randint(0, 23)
            )

            consultation = Consultation.objects.create(
                patient=patient,
                doctor=doctor,
                consultation_type=random.choice(['INITIAL', 'FOLLOW_UP', 'EMERGENCY', 'TELE']),
                priority=random.choice(['A', 'B', 'C']),
                scheduled_datetime=scheduled_date,
                chief_complaint=fake.text(max_nb_chars=200),
                vitals={
                    'blood_pressure': f"{random.randint(110, 140)}/{random.randint(70, 90)}",
                    'temperature': round(random.uniform(36.1, 37.5), 1),
                    'pulse': random.randint(60, 100)
                },
                symptoms=fake.text(max_nb_chars=300),
                diagnosis=fake.text(max_nb_chars=200),
                status=random.choice(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'])
            )

            # Create private notes
            DoctorPrivateNotes.objects.create(
                consultation=consultation,
                clinical_observations=fake.text(),
                differential_diagnosis=fake.text(),
                treatment_rationale=fake.text()
            )

            # Create prescription
            template = self.create_prescription_template(doctor)
            prescription = Prescription.objects.create(
                consultation=consultation,
                template_used=template,
                notes=fake.text(max_nb_chars=200)
            )

            # Create prescription items
            medications = Medication.objects.all()
            stock_items = StockItem.objects.all()
            if medications.exists() and stock_items.exists():
                for i in range(random.randint(1, 5)):
                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication=random.choice(medications),
                        stock_item=random.choice(stock_items),
                        dosage=f"{random.randint(1, 3)} tablet(s)",
                        frequency=f"{random.randint(1, 3)} times daily",
                        duration=f"{random.randint(1, 30)} days",
                        quantity_prescribed=random.randint(10, 100),
                        instructions=fake.text(max_nb_chars=100),
                        order=i
                    )

            # Create treatment plan
            treatment_plan = TreatmentPlan.objects.create(
                consultation=consultation,
                description=fake.text(),
                duration_weeks=random.randint(1, 12),
                goals=fake.text(),
                expected_outcomes=fake.text(),
                total_cost=random.randint(1000, 10000),
                payment_status=random.choice(['PENDING', 'PARTIAL', 'COMPLETED'])
            )

            # Create treatment plan items
            for i in range(random.randint(1, 5)):
                TreatmentPlanItem.objects.create(
                    treatment_plan=treatment_plan,
                    name=random.choice(MEDICAL_PROCEDURES),
                    description=fake.text(),
                    cost=random.randint(100, 1000),
                    order=i
                )

            # Create staff instructions
            StaffInstruction.objects.create(
                consultation=consultation,
                pre_consultation=fake.text(),
                during_consultation=fake.text(),
                post_consultation=fake.text(),
                priority=random.choice(['A', 'B', 'C'])
            )

            return consultation

        except Exception as e:
            logger.error(f"Error creating consultation data: {str(e)}")
            raise

    def handle(self, *args, **options):
        num_consultations = options['consultations']
        successful = 0
        failed = 0

        self.stdout.write(f"Starting to create {num_consultations} consultations...")

        for i in range(num_consultations):
            try:
                with transaction.atomic():
                    consultation = self.create_consultation_data()
                    successful += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created consultation {i+1}/{num_consultations} "
                            f"for patient {consultation.patient.get_full_name()}"
                        )
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to create consultation {i+1}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted: Successfully created {successful} consultations "
                f"({failed} failed)"
            )
        )
