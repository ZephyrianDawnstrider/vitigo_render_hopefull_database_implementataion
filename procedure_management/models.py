# Standard library imports
import logging
from decimal import Decimal

# Django imports
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

# Initialize logger
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()

class ProcedureCategory(models.Model):
    """Categories of medical procedures"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Procedure Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class ProcedureType(models.Model):
    """Specific types of procedures within categories"""
    PRIORITY_CHOICES = [
        ('A', 'Blue A - High Priority'),
        ('B', 'Green B - Medium Priority'),
        ('C', 'Red C - Low Priority'),
    ]

    category = models.ForeignKey(
        ProcedureCategory,
        on_delete=models.PROTECT,
        related_name='procedure_types'
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField()
    base_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    priority = models.CharField(
        max_length=1,
        choices=PRIORITY_CHOICES,
        default='B'
    )
    requires_consent = models.BooleanField(default=True)
    requires_fasting = models.BooleanField(default=False)
    recovery_time_minutes = models.PositiveIntegerField()
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low Risk'),
            ('MODERATE', 'Moderate Risk'),
            ('HIGH', 'High Risk')
        ]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['category', 'name']
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"

class ProcedurePrerequisite(models.Model):
    """Prerequisites for procedures"""
    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE,
        related_name='prerequisites'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_mandatory = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['procedure_type', 'order']

    def __str__(self):
        return f"{self.procedure_type.name} - {self.name}"

class ProcedureInstruction(models.Model):
    """Instructions for before and after procedures"""
    INSTRUCTION_TYPE = [
        ('PRE', 'Pre-procedure'),
        ('POST', 'Post-procedure'),
    ]

    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE,
        related_name='instructions'
    )
    instruction_type = models.CharField(max_length=4, choices=INSTRUCTION_TYPE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['procedure_type', 'instruction_type', 'order']

    def __str__(self):
        return f"{self.get_instruction_type_display()} - {self.title}"

class Procedure(models.Model):
    """Individual procedure instances"""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONSENT_PENDING', 'Consent Pending'),
        ('READY', 'Ready to Start'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE,  # Changed from SET_NULL to CASCADE
        related_name='procedures'
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,  # Changed from SET_NULL to CASCADE
        related_name='procedures',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    appointment = models.OneToOneField(
        'appointment_management.Appointment',
        on_delete=models.CASCADE,  # Changed from SET_NULL to CASCADE
        related_name='procedure'
    )
    
    # Staff assignments
    primary_doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='primary_procedures',
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    assisting_staff = models.ManyToManyField(
        User,
        related_name='assisted_procedures',
        blank=True
    )
    
    # Timing information
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )
    notes = models.TextField(blank=True)
    complications = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    
    # Cost and billing
    final_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Payment Pending'),
            ('PARTIAL', 'Partially Paid'),
            ('COMPLETED', 'Payment Completed'),
            ('REFUNDED', 'Refunded')
        ],
        default='PENDING'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_procedures'
    )

    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['primary_doctor', 'status']),
        ]

    def __str__(self):
        return f"{self.procedure_type.name} for {self.patient} on {self.scheduled_date}"

    def clean(self):
        try:
            if self.actual_end_time and self.actual_start_time and self.actual_end_time < self.actual_start_time:
                raise ValidationError("End time cannot be earlier than start time")
        except Exception as e:
            logger.error(f"Validation error in Procedure: {str(e)}")
            raise

class ConsentForm(models.Model):
    """Patient consent forms for procedures"""
    procedure = models.OneToOneField(
        Procedure,
        on_delete=models.CASCADE,
        related_name='consent_form'
    )
    signed_by_patient = models.BooleanField(default=False)
    patient_signature = models.ImageField(
        upload_to='procedure_consents/signatures/',
        null=True,
        blank=True
    )
    signed_datetime = models.DateTimeField(null=True, blank=True)
    witness_name = models.CharField(max_length=100, blank=True)
    witness_signature = models.ImageField(
        upload_to='procedure_consents/signatures/',
        null=True,
        blank=True
    )
    scanned_document = models.FileField(
        upload_to='procedure_consents/documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consent for {self.procedure}"

class ProcedureChecklistTemplate(models.Model):
    """Templates for procedure checklists"""
    procedure_type = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE,
        related_name='checklist_templates'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.procedure_type.name} - {self.name}"

class ChecklistItem(models.Model):
    """Individual items in procedure checklists"""
    template = models.ForeignKey(
        ProcedureChecklistTemplate,
        on_delete=models.CASCADE,
        related_name='items'
    )
    description = models.CharField(max_length=500)
    is_mandatory = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['template', 'order']

    def __str__(self):
        return f"{self.template.name} - {self.description[:50]}"

class ProcedureChecklist(models.Model):
    """Completed checklists for specific procedures"""
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        related_name='checklists'
    )
    template = models.ForeignKey(
        ProcedureChecklistTemplate,
        on_delete=models.PROTECT
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['procedure', 'template']

    def __str__(self):
        return f"Checklist for {self.procedure}"

class CompletedChecklistItem(models.Model):
    """Status of individual checklist items"""
    checklist = models.ForeignKey(
        ProcedureChecklist,
        on_delete=models.CASCADE,
        related_name='completed_items'
    )
    item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.PROTECT
    )
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['checklist', 'item']

class ProcedureMedia(models.Model):
    """Media files associated with procedures"""
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        related_name='media_files'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file_type = models.CharField(
        max_length=20,
        choices=[
            ('IMAGE', 'Image'),
            ('VIDEO', 'Video'),
            ('DOCUMENT', 'Document'),
            ('OTHER', 'Other')
        ]
    )
    file = models.FileField(
        upload_to='procedure_media/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mov']
        )]
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(
        default=True,
        help_text="Whether the file is for internal use only"
    )

    class Meta:
        verbose_name_plural = "Procedure Media"

    def __str__(self):
        return f"{self.procedure} - {self.title}"