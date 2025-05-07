# image_management/management/commands/populate_image_data.py

import random
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files import File
from PIL import Image
from django.conf import settings
from user_management.models import CustomUser
from patient_management.models import Patient
from image_management.models import (
    BodyPart, ImageTag, PatientImage, ImageComparison, ComparisonImage, ImageAnnotation
)
from faker import Faker
from access_control.models import Role
from django.db import transaction

fake = Faker()

class Command(BaseCommand):
    help = 'Generate sample image management data for patients'

    def add_arguments(self, parser):
        parser.add_argument('--patient_email', type=str, help='Email of specific patient to generate data for')
        parser.add_argument('--images', type=int, default=5, help='Number of images per patient')

    def handle(self, *args, **kwargs):
        patient_email = kwargs.get('patient_email')
        images_per_patient = kwargs.get('images')

        # Ensure we have necessary roles
        patient_role, _ = Role.objects.get_or_create(
            name='PATIENT',
            defaults={'display_name': 'Patient', 'template_folder': 'patient'}
        )
        doctor_role, _ = Role.objects.get_or_create(
            name='DOCTOR',
            defaults={'display_name': 'Doctor', 'template_folder': 'doctor'}
        )

        # Create or get sample body parts and tags
        self.create_sample_metadata()

        # Get patients to process
        if patient_email:
            patients = Patient.objects.filter(user__email=patient_email)
            if not patients.exists():
                self.stdout.write(self.style.ERROR(f'No patient found with email {patient_email}'))
                return
        else:
            patients = Patient.objects.all()

        # Create sample images for each patient
        for patient in patients:
            self.generate_patient_images(patient, images_per_patient)
            self.stdout.write(
                self.style.SUCCESS(f'Generated {images_per_patient} images for patient {patient.user.email}')
            )

    def create_sample_metadata(self):
        # Create body parts
        body_parts = [
            'Face', 'Neck', 'Chest', 'Back', 'Arms', 'Hands', 
            'Legs', 'Feet', 'Abdomen', 'Scalp'
        ]
        for part in body_parts:
            BodyPart.objects.get_or_create(
                name=part,
                defaults={'description': f'The {part.lower()} region'}
            )

        # Create image tags
        tags = [
            'Before Treatment', 'After Treatment', 'Progress', 
            'Critical Area', 'Improving', 'New Spots'
        ]
        for tag in tags:
            ImageTag.objects.get_or_create(name=tag)

    def generate_patient_images(self, patient, count):
        # Ensure sample image directory exists
        sample_dir = os.path.join(settings.MEDIA_ROOT, 'sample_images')
        os.makedirs(sample_dir, exist_ok=True)

        # Create a sample image if it doesn't exist
        sample_path = os.path.join(sample_dir, 'vitiligo_sample.jpg')
        if not os.path.exists(sample_path):
            img = Image.new('RGB', (800, 600), color='white')
            img.save(sample_path)

        # Get random doctor for assignments
        doctor = CustomUser.objects.filter(role__name='DOCTOR').first()
        
        for _ in range(count):
            # Create patient image
            with open(sample_path, 'rb') as img_file:
                image = PatientImage.objects.create(
                    patient=patient,
                    image_file=File(img_file, name=f'patient_{patient.id}_image_{_}.jpg'),
                    body_part=BodyPart.objects.order_by('?').first(),
                    image_type=random.choice(['CLINIC', 'PATIENT']),
                    date_taken=fake.date_between(start_date='-1y', end_date='today'),
                    notes=fake.text(max_nb_chars=200),
                    uploaded_by=doctor,
                    is_private=random.choice([True, False])
                )

            # Add random tags
            tags = ImageTag.objects.order_by('?')[:random.randint(1, 3)]
            image.tags.set(tags)

            # Create annotations
            self.create_annotations(image, doctor)

        # Create image comparison
        self.create_image_comparison(patient, doctor)

    def create_annotations(self, image, doctor):
        for _ in range(random.randint(1, 3)):
            # Generate coordinates that ensure annotation stays within bounds
            width = random.uniform(5, 15)  # Reduced max width
            height = random.uniform(5, 15)  # Reduced max height
            x_coordinate = random.uniform(0, 100 - width)  # Ensure x + width <= 100
            y_coordinate = random.uniform(0, 100 - height)  # Ensure y + height <= 100
            
            ImageAnnotation.objects.create(
                image=image,
                x_coordinate=x_coordinate,
                y_coordinate=y_coordinate,
                width=width,
                height=height,
                text=fake.sentence(),
                created_by=doctor
            )

    def create_image_comparison(self, patient, doctor):
        # Get existing images for this patient
        patient_images = PatientImage.objects.filter(patient=patient)
        if patient_images.count() < 2:
            return  # Skip if not enough images
            
        # Select two random images
        selected_images = list(patient_images.order_by('?')[:2])
        
        try:
            with transaction.atomic():
                # Create comparison
                comparison = ImageComparison.objects.create(
                    title=f"Progress Comparison - {fake.date()}", 
                    description=fake.text(),
                    created_by=doctor
                )

                # Add the images through the through model
                for idx, image in enumerate(selected_images, 1):
                    ComparisonImage.objects.create(
                        comparison=comparison,
                        image=image,
                        order=idx
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created comparison for patient {patient.user.email}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to create comparison for {patient.user.email}: {str(e)}'
                )
            )