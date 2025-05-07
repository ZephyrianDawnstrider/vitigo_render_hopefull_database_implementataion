# Standard library imports
import logging

# Django core imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

# Local application imports
from pharmacy_management.models import Medication
from phototherapy_management.models import PhototherapySession
from stock_management.models import StockItem

# Initialize logger and User model
User = get_user_model()
logger = logging.getLogger(__name__)

class ConsultationPriority(models.TextChoices):
    HIGH = 'A', 'Blue A - High Priority'
    MEDIUM = 'B', 'Green B - Medium Priority'
    LOW = 'C', 'Red C - Low Priority'

class ConsultationType(models.TextChoices):
    INITIAL = 'INITIAL', 'Initial Consultation'
    FOLLOW_UP = 'FOLLOW_UP', 'Follow-up Consultation'
    EMERGENCY = 'EMERGENCY', 'Emergency Consultation'
    TELE = 'TELE', 'Tele-consultation'

class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Payment Pending'
    PARTIAL = 'PARTIAL', 'Partially Paid'
    COMPLETED = 'COMPLETED', 'Payment Completed'
    CANCELLED = 'CANCELLED', 'Payment Cancelled'

class Consultation(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show')
    ]
    
    # Base Information
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consultations',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_consultations',
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    consultation_type = models.CharField(
        max_length=20,
        choices=ConsultationType.choices,
        default=ConsultationType.INITIAL
    )
    priority = models.CharField(
        max_length=1,
        choices=ConsultationPriority.choices,
        default=ConsultationPriority.MEDIUM
    )
    
    center = models.ForeignKey(
        'appointment_management.Center',
        on_delete=models.CASCADE,
        related_name='consultations',
        null=True,
        blank=True
    )
    
    time_slot = models.ForeignKey(
        'appointment_management.DoctorTimeSlot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultations'
    )
    
    # Timing Information
    scheduled_datetime = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Clinical Information
    chief_complaint = models.TextField()
    vitals = models.JSONField(
        null=True,
        blank=True,
        help_text="Store vital signs as JSON: BP, pulse, temperature, etc."
    )
    symptoms = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    diagnosis = models.TextField()
    
    # Follow-up Information
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Patient Instructions
    patient_instructions = models.TextField(
        blank=True,
        help_text="Instructions for the patient to follow"
    )
    lifestyle_instructions = models.TextField(
        blank=True,
        help_text="Lifestyle and dietary instructions for the patient"
    )
    care_instructions = models.TextField(
        blank=True,
        help_text="Care and precaution instructions"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_consultations'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration_minutes = models.IntegerField(default=30)

    class Meta:
        ordering = ['-scheduled_datetime']
        indexes = [
            models.Index(fields=['scheduled_datetime', 'status']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
        ]

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.scheduled_datetime.date()}"

    def clean(self):
        if self.follow_up_date and self.follow_up_date < self.scheduled_datetime.date():
            raise ValidationError("Follow-up date cannot be earlier than consultation date")

class DoctorPrivateNotes(models.Model):
    """Secure notes only accessible to the consulting doctor"""
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='private_notes'
    )
    clinical_observations = models.TextField(blank=True)
    differential_diagnosis = models.TextField(blank=True)
    treatment_rationale = models.TextField(blank=True)
    private_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_private_notes", "Can view doctor's private notes"),
        ]

class PrescriptionTemplate(models.Model):
    """Reusable prescription templates"""
    name = models.CharField(max_length=100)
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prescription_templates',
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    description = models.TextField(blank=True)
    is_global = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by Dr. {self.doctor.get_full_name()}"

class TemplateItem(models.Model):
    """Individual items within a prescription template"""
    template = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE
    )
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Prescription(models.Model):
    """Actual prescriptions linked to consultations"""
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    template_used = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Prescription for {self.consultation}"

class PrescriptionItem(models.Model):
    """Individual items within a prescription"""
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE
    )
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prescription_items'
    )
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity_prescribed = models.PositiveIntegerField()
    instructions = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

class TreatmentPlan(models.Model):
    """Comprehensive treatment plan including costs"""
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='treatment_plan'
    )
    description = models.TextField()
    duration_weeks = models.PositiveIntegerField()
    goals = models.TextField()
    lifestyle_modifications = models.TextField(blank=True)
    dietary_recommendations = models.TextField(blank=True)
    exercise_recommendations = models.TextField(blank=True)
    expected_outcomes = models.TextField()
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TreatmentPlanItem(models.Model):
    """Individual items within a treatment plan"""
    treatment_plan = models.ForeignKey(
        TreatmentPlan,
        on_delete=models.CASCADE,
        related_name='items'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class StaffInstruction(models.Model):
    """Instructions for staff regarding the consultation"""
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='staff_instructions'
    )
    pre_consultation = models.TextField(
        blank=True,
        help_text="Instructions for staff before consultation"
    )
    during_consultation = models.TextField(
        blank=True,
        help_text="Instructions for staff during consultation"
    )
    post_consultation = models.TextField(
        blank=True,
        help_text="Instructions for staff after consultation"
    )
    priority = models.CharField(
        max_length=1,
        choices=ConsultationPriority.choices,
        default=ConsultationPriority.MEDIUM
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ConsultationPhototherapy(models.Model):
    """Link between consultations and phototherapy sessions"""
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='phototherapy_sessions'
    )
    phototherapy_session = models.ForeignKey(
        PhototherapySession,
        on_delete=models.CASCADE,
        related_name='consultations'
    )
    instructions = models.TextField()
    schedule = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['consultation', 'phototherapy_session']

class ConsultationAttachment(models.Model):
    """Files and documents related to the consultation"""
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='consultation_attachments/')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file_type = models.CharField(max_length=50, default='unknown') 
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.consultation}"

class ConsultationFeedback(models.Model):
    """Patient feedback and ratings for consultations"""
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5)
        ],
        help_text="Patient satisfaction rating (0-5)"
    )
    comments = models.TextField(
        blank=True,
        help_text="Patient comments and feedback"
    )
    service_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating for service quality (1-5)"
    )
    doctor_communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating for doctor's communication (1-5)"
    )
    wait_time_satisfaction = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating for wait time satisfaction (1-5)"
    )
    would_recommend = models.BooleanField(
        default=True,
        help_text="Whether patient would recommend the doctor"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='consultation_feedbacks'
    )

    class Meta:
        indexes = [
            models.Index(fields=['consultation', 'rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Feedback for {self.consultation}"

    def clean(self):
        if self.consultation.status != 'COMPLETED':
            raise ValidationError("Feedback can only be given for completed consultations")