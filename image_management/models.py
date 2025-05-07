# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

# Third-party imports
from PIL import Image as PILImage
import os

# Local app imports
from consultation_management.models import Consultation
from patient_management.models import Patient

# Get user model
User = get_user_model()


class BodyPart(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ImageTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class PatientImage(models.Model):
    UPLOAD_TYPE_CHOICES = [
        ('PROGRESS', 'Progress Update'),
        ('PROBLEM', 'Problem Report')
    ]

    IMAGE_TYPE_CHOICES = [
        ('CLINIC', 'Clinic Taken'),
        ('PATIENT', 'Patient Uploaded'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='images',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    image_file = models.ImageField(upload_to='patient_images/')
    body_part = models.ForeignKey(BodyPart, on_delete=models.SET_NULL, null=True)
    image_type = models.CharField(max_length=10, choices=IMAGE_TYPE_CHOICES)
    upload_type = models.CharField(
        max_length=10, 
        choices=UPLOAD_TYPE_CHOICES,
        default='PROGRESS'
    )
    date_taken = models.DateField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(ImageTag, blank=True)
    tagged_users = models.ManyToManyField(User, blank=True)
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True)

    # Metadata
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='uploaded_images')
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return f"Image of {self.patient.user.get_full_name()} - {self.body_part} on {self.date_taken}"

    def clean(self):
        # Validate file size (max 5MB as per settings)
        if self.image_file and self.image_file.size > settings.MAX_UPLOAD_SIZE:
            raise ValidationError(f'Image file size cannot exceed {settings.MAX_UPLOAD_SIZE/1024/1024}MB.')
        
        # Validate file extension
        ext = os.path.splitext(self.image_file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            raise ValidationError('Only JPG, JPEG and PNG files are allowed.')

    def extract_metadata(self):
        if self.image_file:
            with PILImage.open(self.image_file) as img:
                self.width = img.width
                self.height = img.height
                self.file_size = self.image_file.size

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.pk:  # Only on creation
            self.extract_metadata()
        super().save(*args, **kwargs)

    @classmethod
    def get_consultation_images(cls, consultation_id):
        return cls.objects.filter(consultation_id=consultation_id).order_by('date_taken')


class ImageComparison(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    images = models.ManyToManyField(PatientImage, through='ComparisonImage')

    comparison_type = models.CharField(
        max_length=20,
        choices=[
            ('individual', 'Individual Images'),
            ('consultation', 'Consultation Based')
        ],
        default='individual'
    )

    def __str__(self):
        return self.title

    def clean(self):
        if self.comparison_type == 'individual' and self.images.count() > 4:
            raise ValidationError('Cannot compare more than 4 images in individual comparison')
        elif self.comparison_type == 'consultation' and self.images.count() > 8:
            raise ValidationError('Cannot compare more than 8 images in consultation comparison')

class ComparisonImage(models.Model):
    comparison = models.ForeignKey(ImageComparison, on_delete=models.CASCADE)
    image = models.ForeignKey(PatientImage, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ('comparison', 'image')

    def __str__(self):
        return f"Image {self.order} in {self.comparison.title}"


class ImageAnnotation(models.Model):
    image = models.ForeignKey(PatientImage, on_delete=models.CASCADE, related_name='annotations')
    x_coordinate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    y_coordinate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    width = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    height = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    text = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Annotation for {self.image} at ({self.x_coordinate}, {self.y_coordinate})"

    def clean(self):
        # Validate annotation boundaries
        if (self.x_coordinate + self.width) > 100:
            raise ValidationError('Annotation exceeds image width boundary')
        if (self.y_coordinate + self.height) > 100:
            raise ValidationError('Annotation exceeds image height boundary')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)