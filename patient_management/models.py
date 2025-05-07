from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='patient_profile',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, null=True, blank=True)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_number = models.CharField(max_length=15)

    # Vitiligo-specific fields
    vitiligo_onset_date = models.DateField(null=True, blank=True)
    vitiligo_type = models.CharField(max_length=50, null=True, blank=True)
    affected_body_areas = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.email}"


class MedicalHistory(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='medical_history')
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    past_surgeries = models.TextField(blank=True)
    family_history = models.TextField(blank=True)


class Medication(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    prescribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                      related_name='prescribed_medications')

    def __str__(self):
        return f"{self.name} - {self.dosage}"


class VitiligoAssessment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitiligo_assessments')
    assessment_date = models.DateField()
    body_surface_area_affected = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    vasi_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    treatment_response = models.TextField()
    notes = models.TextField(blank=True)
    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Assessment for {self.patient.user.get_full_name()} on {self.assessment_date}"


class TreatmentPlan(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatment_plans')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    treatment_goals = models.TextField()
    medications = models.ManyToManyField(Medication, blank=True)
    phototherapy_details = models.TextField(blank=True)
    lifestyle_recommendations = models.TextField(blank=True)
    follow_up_frequency = models.CharField(max_length=50)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Treatment Plan for {self.patient.user.get_full_name()} created on {self.created_date}"