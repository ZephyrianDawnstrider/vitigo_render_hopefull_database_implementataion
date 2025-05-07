# telemedicine_management/management/commands/populate_telemedicine_data.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from patient_management.models import Patient
from telemedicine_management.models import (
    TeleconsultationSession, TeleconsultationPrescription, TeleconsultationFile, TeleconsultationFeedback, TelemedicinevirtualWaitingRoom
)

class Command(BaseCommand):
    help = 'Generate sample telemedicine management data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample telemedicine management data...')

        # Fetch all patients and doctors
        patients = Patient.objects.all()
        doctors = CustomUser.objects.filter(role='DOCTOR')

        # Create sample teleconsultation sessions
        for _ in range(10):  # Generate 10 sample teleconsultation sessions
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            scheduled_start = timezone.now() - timezone.timedelta(days=random.randint(0, 30))
            scheduled_end = scheduled_start + timezone.timedelta(hours=1)
            actual_start = scheduled_start + timezone.timedelta(minutes=random.randint(0, 30))
            actual_end = actual_start + timezone.timedelta(minutes=random.randint(30, 60))
            status = random.choice(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'])
            teleconsultation = TeleconsultationSession.objects.create(
                patient=patient,
                doctor=doctor,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                actual_start=actual_start if status == 'COMPLETED' else None,
                actual_end=actual_end if status == 'COMPLETED' else None,
                status=status,
                video_call_link='https://example.com/video_call',
                is_recorded=random.choice([True, False]),
                recording_url='https://example.com/recording' if random.choice([True, False]) else None,
                notes='Sample teleconsultation notes'
            )

            # Create sample teleconsultation prescriptions
            TeleconsultationPrescription.objects.create(
                teleconsultation=teleconsultation,
                prescription_text='Sample prescription text'
            )

            # Create sample teleconsultation files
            for _ in range(random.randint(1, 3)):  # Add 1 to 3 files to each teleconsultation
                TeleconsultationFile.objects.create(
                    teleconsultation=teleconsultation,
                    file='path/to/sample_file.pdf',
                    file_type=random.choice(['LAB_RESULT', 'MEDICAL_RECORD', 'PRESCRIPTION', 'OTHER']),
                    uploaded_by=random.choice([patient.user, doctor]),
                    description='Sample file description'
                )

            # Create sample teleconsultation feedback
            if status == 'COMPLETED':
                TeleconsultationFeedback.objects.create(
                    teleconsultation=teleconsultation,
                    rating=random.randint(1, 5),
                    comments='Sample feedback comments',
                    submitted_by=patient.user
                )

            # Create sample virtual waiting room entries
            if not TelemedicinevirtualWaitingRoom.objects.filter(patient=patient).exists():
                TelemedicinevirtualWaitingRoom.objects.create(
                    patient=patient,
                    teleconsultation=teleconsultation,
                    is_active=random.choice([True, False])
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample telemedicine management data'))