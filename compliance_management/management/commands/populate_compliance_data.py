from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta
import random
import json

from compliance_management.models import (
    ComplianceSchedule,
    ComplianceNote,
    ComplianceIssue,
    ComplianceMetric,
    ComplianceReminder,
    ComplianceReport,
    PatientGroup,
    ComplianceAlert
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates sample data for compliance management module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patients',
            type=int,
            default=10,
            help='Number of patients to create compliance data for'
        )

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Clear existing data
                self.stdout.write('Clearing existing compliance data...')
                ComplianceSchedule.objects.all().delete()
                ComplianceNote.objects.all().delete()
                ComplianceIssue.objects.all().delete()
                ComplianceMetric.objects.all().delete()
                ComplianceReminder.objects.all().delete()
                ComplianceReport.objects.all().delete()
                PatientGroup.objects.all().delete()
                ComplianceAlert.objects.all().delete()

                # Get users
                patients = User.objects.filter(role__name='PATIENT')[:options['patients']]
                staff = User.objects.filter(is_staff=True)

                if not patients.exists():
                    self.stdout.write(self.style.ERROR('No patients found'))
                    return

                if not staff.exists():
                    self.stdout.write(self.style.ERROR('No staff members found'))
                    return

                # Create sample data for each patient
                for patient in patients:
                    self.create_patient_compliance_data(patient, staff)

                self.stdout.write(self.style.SUCCESS('Successfully populated compliance data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))

    def create_patient_compliance_data(self, patient, staff):
        today = timezone.now().date()
        
        # Create ComplianceSchedule
        for _ in range(random.randint(3, 7)):
            schedule_date = today + timedelta(days=random.randint(-30, 30))
            schedule = ComplianceSchedule.objects.create(
                patient=patient,
                assigned_to=random.choice(staff),
                scheduled_date=schedule_date,
                scheduled_time=timezone.now().time(),
                actual_date=schedule_date if random.random() > 0.3 else None,
                actual_time=timezone.now().time() if random.random() > 0.3 else None,
                duration_minutes=random.choice([15, 30, 45, 60]),
                priority=random.choice(['A', 'B', 'C']),
                status=random.choice(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'MISSED', 'RESCHEDULED', 'CANCELLED']),
                schedule_notes=f"Sample schedule notes for {patient.get_full_name()}",
                outcome="Sample outcome" if random.random() > 0.5 else "",
                next_follow_up_date=schedule_date + timedelta(days=random.randint(7, 30))
            )

            # Create ComplianceNotes for each schedule
            for _ in range(random.randint(1, 3)):
                ComplianceNote.objects.create(
                    schedule=schedule,
                    note_type=random.choice(['GENERAL', 'FOLLOW_UP', 'CONCERN', 'RESOLUTION']),
                    content=f"Sample note content for {patient.get_full_name()}",
                    created_by=random.choice(staff),
                    is_private=random.choice([True, False])
                )

        # Create ComplianceIssues
        for _ in range(random.randint(1, 4)):
            issue = ComplianceIssue.objects.create(
                patient=patient,
                title=f"Sample compliance issue for {patient.get_full_name()}",
                description="Detailed description of the compliance issue",
                severity=random.choice(['HIGH', 'MEDIUM', 'LOW']),
                status=random.choice(['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']),
                assigned_to=random.choice(staff),
                resolution="Issue resolution details" if random.random() > 0.5 else "",
                resolved_at=timezone.now() if random.random() > 0.5 else None,
                resolved_by=random.choice(staff) if random.random() > 0.5 else None
            )

        # Create ComplianceMetrics
        metric_types = ['MEDICATION', 'APPOINTMENT', 'PHOTOTHERAPY', 'FOLLOW_UP', 'OVERALL']
        for metric_type in metric_types:
            ComplianceMetric.objects.create(
                patient=patient,
                metric_type=metric_type,
                evaluation_date=today,
                compliance_score=random.uniform(60.0, 100.0),
                evaluation_period_start=today - timedelta(days=30),
                evaluation_period_end=today,
                notes=f"Sample compliance metric notes for {metric_type}",
                evaluated_by=random.choice(staff)
            )

        # Create ComplianceReminders
        reminder_types = ['MEDICATION', 'APPOINTMENT', 'FOLLOW_UP', 'PHOTOTHERAPY', 'GENERAL']
        for reminder_type in reminder_types:
            ComplianceReminder.objects.create(
                patient=patient,
                reminder_type=reminder_type,
                scheduled_datetime=timezone.now() + timedelta(days=random.randint(1, 30)),
                message=f"Sample reminder message for {reminder_type}",
                status=random.choice(['PENDING', 'SENT', 'FAILED', 'CANCELLED']),
                sent_at=timezone.now() if random.random() > 0.5 else None,
                delivery_status='DELIVERED' if random.random() > 0.5 else None,
                error_message="Sample error message" if random.random() > 0.8 else ""
            )

        # Create ComplianceAlerts
        for _ in range(random.randint(1, 3)):
            ComplianceAlert.objects.create(
                patient=patient,
                alert_type=random.choice([
                    'MISSED_APPOINTMENT', 'LOW_COMPLIANCE', 'MISSED_MEDICATION',
                    'FOLLOW_UP_NEEDED', 'CRITICAL_ISSUE'
                ]),
                severity=random.choice(['HIGH', 'MEDIUM', 'LOW']),
                message=f"Sample alert message for {patient.get_full_name()}",
                is_resolved=random.choice([True, False]),
                resolved_at=timezone.now() if random.random() > 0.5 else None,
                resolved_by=random.choice(staff) if random.random() > 0.5 else None,
                resolution_notes="Sample resolution notes" if random.random() > 0.5 else ""
            )

        # Create ComplianceReports
        ComplianceReport.objects.create(
            report_type=random.choice(['INDIVIDUAL', 'GROUP', 'SUMMARY', 'TREND']),
            title=f"Compliance Report for {patient.get_full_name()}",
            description="Sample report description",
            parameters={
                'patient_id': patient.id,
                'start_date': (today - timedelta(days=30)).isoformat(),
                'end_date': today.isoformat()
            },
            results={
                'compliance_score': random.uniform(60.0, 100.0),
                'metrics': {
                    'medication': random.uniform(60.0, 100.0),
                    'appointment': random.uniform(60.0, 100.0),
                    'overall': random.uniform(60.0, 100.0)
                }
            },
            generated_by=random.choice(staff),
            period_start=today - timedelta(days=30),
            period_end=today,
            file_path=f"/reports/compliance/{patient.id}_{today.isoformat()}.pdf"
        )

        # Create PatientGroup
        group = PatientGroup.objects.create(
            name=f"Sample Group {random.randint(1, 100)}",
            description="Sample patient group for compliance monitoring",
            criteria={
                'compliance_score_min': 60.0,
                'compliance_score_max': 100.0,
                'priority': random.choice(['A', 'B', 'C'])
            },
            created_by=random.choice(staff),
            is_active=True
        )
        group.patients.add(patient)
