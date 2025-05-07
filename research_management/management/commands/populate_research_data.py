# research_management/management/commands/populate_research_data.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from patient_management.models import Patient
from research_management.models import (
    ResearchStudy, StudyProtocol, PatientStudyEnrollment, DataCollectionPoint, ResearchData, AnalysisResult, Publication
)

class Command(BaseCommand):
    help = 'Generate sample research management data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample research management data...')

        # Fetch all patients and users
        patients = Patient.objects.all()
        users = CustomUser.objects.all()

        # Create sample research studies
        for _ in range(5):  # Generate 5 sample research studies
            principal_investigator = random.choice(users)
            start_date = timezone.now().date() - timezone.timedelta(days=random.randint(0, 365))
            end_date = start_date + timezone.timedelta(days=random.randint(30, 365))
            study = ResearchStudy.objects.create(
                title=f"Study {_ + 1}",
                description='Sample study description',
                start_date=start_date,
                end_date=end_date if random.choice([True, False]) else None,
                principal_investigator=principal_investigator,
                status=random.choice(['PLANNING', 'ACTIVE', 'COMPLETED', 'SUSPENDED', 'TERMINATED']),
                ethics_approval_document='path/to/ethics_approval_document.pdf'
            )

            # Create sample study protocols
            StudyProtocol.objects.create(
                study=study,
                version=f"v{random.randint(1, 5)}",
                document='path/to/study_protocol.pdf',
                approved_date=start_date + timezone.timedelta(days=random.randint(0, 30))
            )

            # Create sample data collection points
            for i in range(random.randint(1, 5)):  # Add 1 to 5 data collection points to each study
                DataCollectionPoint.objects.create(
                    study=study,
                    name=f"Data Collection Point {i + 1}",
                    description='Sample data collection point description',
                    target_date=timezone.timedelta(days=random.randint(1, 100))
                )

            # Create sample patient study enrollments
            num_patients_to_enroll = min(random.randint(1, 10), patients.count())
            for patient in random.sample(list(patients), num_patients_to_enroll):  # Enroll 1 to 10 patients per study
                enrollment_date = start_date + timezone.timedelta(days=random.randint(0, 30))
                enrollment = PatientStudyEnrollment.objects.create(
                    patient=patient,
                    study=study,
                    enrollment_date=enrollment_date,
                    status=random.choice(['SCREENING', 'ENROLLED', 'COMPLETED', 'WITHDRAWN']),
                    withdrawal_reason='Sample withdrawal reason' if random.choice([True, False]) else None
                )

                # Create sample research data
                for collection_point in study.data_collection_points.all():
                    ResearchData.objects.create(
                        enrollment=enrollment,
                        collection_point=collection_point,
                        collected_date=enrollment_date + collection_point.target_date,
                        data={'sample_key': 'sample_value'},
                        collected_by=random.choice(users),
                        notes='Sample research data notes'
                    )

            # Create sample analysis results
            for i in range(random.randint(1, 3)):  # Add 1 to 3 analysis results to each study
                AnalysisResult.objects.create(
                    study=study,
                    title=f"Analysis Result {i + 1}",
                    description='Sample analysis result description',
                    result_data={'sample_key': 'sample_value'},
                    created_by=random.choice(users)
                )

            # Create sample publications
            for i in range(random.randint(1, 3)):  # Add 1 to 3 publications to each study
                Publication.objects.create(
                    study=study,
                    title=f"Publication {i + 1}",
                    authors='Author 1, Author 2, Author 3',
                    journal='Sample Journal',
                    publication_date=timezone.now().date() - timezone.timedelta(days=random.randint(0, 365)),
                    doi=f"10.1234/sample.doi.{i + 1}",
                    url='https://example.com/publication'
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample research management data'))