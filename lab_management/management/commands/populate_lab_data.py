# lab_management/management/commands/generate_lab_data.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from patient_management.models import Patient
from lab_management.models import (
    LabTest, LabOrder, LabOrderItem, LabResult, LabReport, LabReportComment
)

class Command(BaseCommand):
    help = 'Generate sample lab management data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample lab management data...')

        # Create sample lab tests if they don't exist
        lab_tests = [
            {'name': 'Complete Blood Count', 'description': 'Measures various components of blood', 'code': 'CBC', 'price': 50.00},
            {'name': 'Liver Function Test', 'description': 'Assesses liver function', 'code': 'LFT', 'price': 75.00},
            {'name': 'Kidney Function Test', 'description': 'Assesses kidney function', 'code': 'KFT', 'price': 70.00},
        ]
        for test in lab_tests:
            LabTest.objects.get_or_create(
                code=test['code'],
                defaults={
                    'name': test['name'],
                    'description': test['description'],
                    'price': test['price'],
                    'is_active': True
                }
            )

        # Fetch all lab tests, patients, and staff
        lab_tests = LabTest.objects.all()
        patients = Patient.objects.all()
        doctors = CustomUser.objects.filter(role='DOCTOR')
        lab_technicians = CustomUser.objects.filter(role='LAB_TECHNICIAN')

        # Generate sample lab orders
        for _ in range(20):  # Generate 20 sample lab orders
            patient = random.choice(patients)
            ordered_by = random.choice(doctors)
            lab_order = LabOrder.objects.create(
                patient=patient,
                ordered_by=ordered_by,
                status=random.choice(['ORDERED', 'COLLECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']),
                notes='Sample lab order notes'
            )
            for _ in range(random.randint(1, 3)):  # Add 1 to 3 items to each lab order
                lab_test = random.choice(lab_tests)
                LabOrderItem.objects.create(
                    lab_order=lab_order,
                    lab_test=lab_test,
                    price=lab_test.price
                )

        # Generate sample lab results
        lab_order_items = LabOrderItem.objects.all()
        for item in lab_order_items:
            if random.choice([True, False]):  # Randomly decide whether to create a result
                LabResult.objects.create(
                    lab_order_item=item,
                    value=str(random.randint(10, 100)),
                    unit='mg/dL',
                    reference_range='10-100 mg/dL',
                    status=random.choice(['NORMAL', 'ABNORMAL', 'CRITICAL']),
                    performed_by=random.choice(lab_technicians),
                    performed_at=timezone.now(),
                    notes='Sample lab result notes'
                )

        # Generate sample lab reports
        lab_orders = LabOrder.objects.all()
        for order in lab_orders:
            if random.choice([True, False]):  # Randomly decide whether to create a report
                lab_report = LabReport.objects.create(
                    lab_order=order,
                    report_file='path/to/sample_report.pdf',
                    upload_type=random.choice(['MANUAL', 'AUTOMATIC']),
                    uploaded_by=random.choice(lab_technicians),
                    is_sent_to_patient=random.choice([True, False])
                )
                # Generate sample comments for the report
                for _ in range(random.randint(1, 3)):  # Add 1 to 3 comments to each report
                    LabReportComment.objects.create(
                        lab_report=lab_report,
                        comment='Sample comment on lab report',
                        created_by=random.choice(doctors),
                    )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample lab management data'))