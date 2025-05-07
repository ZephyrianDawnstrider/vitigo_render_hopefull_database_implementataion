# doctor_management/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class Specialization(models.Model):
    """Base specialization model for categorizing doctors"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class TreatmentMethodSpecialization(models.Model):
    """Specific treatment methods a doctor specializes in"""
    name = models.CharField(max_length=100)  # e.g., Phototherapy, Medical Management, Surgical
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class BodyAreaSpecialization(models.Model):
    """Areas of the body a doctor specializes in treating"""
    name = models.CharField(max_length=100)  # e.g., Facial, Acral, Genital
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AssociatedConditionSpecialization(models.Model):
    """Related conditions a doctor specializes in treating alongside vitiligo"""
    name = models.CharField(max_length=100)  # e.g., Thyroid, Autoimmune
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class DoctorProfile(models.Model):
    """Extended profile for users with the role of Doctor"""
    EXPERIENCE_CHOICES = (
        ('0-5', '0-5 years'),
        ('5-10', '5-10 years'),
        ('10-15', '10-15 years'),
        ('15+', '15+ years'),
    )

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='doctor_profile', 
        limit_choices_to={'role__name': 'Doctor'}
    )
    registration_number = models.CharField(max_length=50, unique=True)
    qualification = models.CharField(max_length=200)
    experience = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES)
    specializations = models.ManyToManyField(Specialization)
    treatment_methods = models.ManyToManyField(TreatmentMethodSpecialization)
    body_areas = models.ManyToManyField(BodyAreaSpecialization)
    associated_conditions = models.ManyToManyField(AssociatedConditionSpecialization)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    about = models.TextField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    rating = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

    class Meta:
        ordering = ['-rating', '-experience']

class DoctorAvailability(models.Model):
    SHIFT_CHOICES = [
        ('MORNING', 'Morning'),
        ('EVENING', 'Evening'),
    ]
    
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability',
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    day_of_week = models.IntegerField(choices=[(i, i) for i in range(7)])
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('doctor', 'day_of_week', 'shift')

class DoctorReview(models.Model):
    """Patient reviews and ratings for doctors"""
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('doctor', 'patient')
        ordering = ['-created_at']