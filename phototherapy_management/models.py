# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.utils import timezone

# Get the user model and setup logging
User = get_user_model()
logger = logging.getLogger(__name__)

class PhototherapyType(models.Model):
    """Different types of phototherapy treatments available"""
    THERAPY_CHOICES = [
        ('WB_NB', 'Wholebody NB'),
        ('EXCIMER', 'Excimer (TP)'),
        ('HOME_NB', 'Home Based NB'),
        ('SUN_EXP', 'Sun Exposure'),
        ('OTHER', 'Other')
    ]
    
    PRIORITY_CHOICES = [
        ('A', 'Blue A - High Priority'),
        ('B', 'Green B - Medium Priority'),
        ('C', 'Red C - Low Priority')
    ]

    name = models.CharField(max_length=100, unique=True)
    therapy_type = models.CharField(max_length=20, choices=THERAPY_CHOICES)
    description = models.TextField()
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='B')
    requires_rfid = models.BooleanField(
        default=False,
        help_text="Whether this therapy type requires RFID access"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['therapy_type', 'priority']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Phototherapy Type'
        verbose_name_plural = 'Phototherapy Types'

    def __str__(self):
        return f"{self.get_therapy_type_display()} - {self.name}"

class PatientRFIDCard(models.Model):
    """RFID card management for patient access control"""
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'PATIENT'}
    )
    card_number = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    assigned_date = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['is_active', 'expires_at']),
        ]
        verbose_name = 'Patient RFID Card'
        verbose_name_plural = 'Patient RFID Cards'

    def __str__(self):
        return f"Card {self.card_number} - {self.patient.get_full_name()}"
    
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    def record_usage(self):
        self.last_used = timezone.now()
        self.save()

class PhototherapyDevice(models.Model):
    """Management of phototherapy devices/machines"""
    name = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    phototherapy_type = models.ForeignKey(PhototherapyType, on_delete=models.PROTECT)
    location = models.CharField(max_length=100)
    installation_date = models.DateField()
    last_maintenance_date = models.DateField(null=True)
    next_maintenance_date = models.DateField(null=True)
    maintenance_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.model_number}"

    def needs_maintenance(self):
        if not self.next_maintenance_date:
            return False
        return timezone.now().date() >= self.next_maintenance_date

class PhototherapyProtocol(models.Model):
    """Treatment protocols for different types of phototherapy"""
    phototherapy_type = models.ForeignKey(PhototherapyType, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    initial_dose = models.FloatField(help_text="Initial dose in mJ/cm²")
    max_dose = models.FloatField(help_text="Maximum dose in mJ/cm²")
    increment_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage to increase dose each session"
    )
    frequency_per_week = models.PositiveIntegerField(
        help_text="Number of sessions per week"
    )
    duration_weeks = models.PositiveIntegerField(
        help_text="Total duration in weeks"
    )
    contraindications = models.TextField(blank=True)
    safety_guidelines = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['phototherapy_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.phototherapy_type.name}"

    def clean(self):
        if self.initial_dose > self.max_dose:
            raise ValidationError("Initial dose cannot exceed maximum dose")
        
class PhototherapyPackage(models.Model):
    """Pre-defined packages for phototherapy treatment plans"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    number_of_sessions = models.PositiveIntegerField()
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured packages are shown first in the list"
    )
    therapy_type = models.ForeignKey(
        PhototherapyType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional: Specific therapy type this package is for"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', 'number_of_sessions']
        indexes = [
            models.Index(fields=['is_active', 'is_featured']),
        ]

    def __str__(self):
        return f"{self.name} - {self.number_of_sessions} sessions"
    

class PhototherapyPlan(models.Model):
    """Treatment plans for patients"""
    BILLING_STATUS = [
        ('PENDING', 'Payment Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('OVERDUE', 'Payment Overdue')
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'PATIENT'},
        related_name='phototherapy_plans'
    )
    protocol = models.ForeignKey(PhototherapyProtocol, on_delete=models.PROTECT)
    rfid_card = models.ForeignKey(
        PatientRFIDCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True)
    current_dose = models.FloatField()
    total_sessions_planned = models.PositiveIntegerField()
    sessions_completed = models.PositiveIntegerField(default=0)
    
    # Billing information
    billing_status = models.CharField(
        max_length=20,
        choices=BILLING_STATUS,
        default='PENDING'
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    
    # Instructions and notes
    special_instructions = models.TextField(blank=True)
    doctor_notes = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)
    
    # Reminder settings
    reminder_frequency = models.IntegerField(
        default=1,
        help_text="Reminder frequency in days"
    )
    last_reminder_sent = models.DateTimeField(null=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_phototherapy_plans'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    center = models.ForeignKey(
        'PhototherapyCenter',
        on_delete=models.PROTECT,
        related_name='treatment_plans',
        null=True,
        blank=True,
        help_text="Select the phototherapy center where treatment will be administered"
    )

    class Meta:
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['billing_status']),
        ]

    def __str__(self):
        return f"Plan for {self.patient.get_full_name()} - {self.protocol.name}"

    def update_sessions_completed(self):
        """Update the sessions_completed count based on actual completed sessions"""
        completed_count = self.sessions.filter(status='COMPLETED').count()
        if completed_count != self.sessions_completed:
            self.sessions_completed = completed_count
            self.save(update_fields=['sessions_completed'])
        return self.sessions_completed

    def get_completion_percentage(self):
        """Calculate completion percentage based on actual completed sessions"""
        if self.total_sessions_planned == 0:
            return 0
        completed = self.update_sessions_completed()  # Ensure count is up to date
        return round((completed / self.total_sessions_planned) * 100)

    def get_payment_percentage(self):
        if self.total_cost == 0:
            return 100
        return (float(self.amount_paid) / float(self.total_cost)) * 100

class PhototherapySession(models.Model):
    """Individual phototherapy treatment sessions"""
    COMPLIANCE_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed'),
        ('RESCHEDULED', 'Rescheduled'),
        ('CANCELLED', 'Cancelled')
    ]
    
    PROBLEM_SEVERITY = [
        ('NONE', 'No Problems'),
        ('MILD', 'Mild Issues'),
        ('MODERATE', 'Moderate Issues'),
        ('SEVERE', 'Severe Issues')
    ]

    plan = models.ForeignKey(
        PhototherapyPlan,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_number = models.PositiveIntegerField()
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    actual_date = models.DateField(null=True)
    
    # Treatment details
    device = models.ForeignKey(
        PhototherapyDevice,
        on_delete=models.SET_NULL,
        null=True
    )
    planned_dose = models.FloatField()
    actual_dose = models.FloatField(null=True)
    duration_seconds = models.PositiveIntegerField(null=True)
    
    # Status and compliance
    status = models.CharField(
        max_length=20,
        choices=COMPLIANCE_CHOICES,
        default='SCHEDULED'
    )
    
    # Problem reporting
    problem_severity = models.CharField(
        max_length=20,
        choices=PROBLEM_SEVERITY,
        default='NONE'
    )
    side_effects = models.TextField(blank=True)
    problems_reported = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)
    remarks = models.TextField(
        blank=True,
        help_text="Additional remarks or comments about the session"
    )
    
    # RFID tracking
    rfid_entry_time = models.DateTimeField(null=True)
    rfid_exit_time = models.DateTimeField(null=True)
    
    # Staff assignment
    administered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='administered_phototherapy_sessions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['plan', 'status']),
            models.Index(fields=['scheduled_date', 'status']),
        ]

    def __str__(self):
        return f"Session {self.session_number} for {self.plan.patient.get_full_name()}"

    def clean(self):
        try:
            if self.actual_dose and self.actual_dose > self.plan.protocol.max_dose:
                raise ValidationError("Dose exceeds maximum allowed")
            
            if self.rfid_entry_time and self.rfid_exit_time:
                if self.rfid_exit_time <= self.rfid_entry_time:
                    raise ValidationError("Exit time must be after entry time")
                
            if self.status == 'COMPLETED' and not self.actual_dose:
                raise ValidationError("Completed sessions must have an actual dose recorded")
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            raise

class HomePhototherapyLog(models.Model):
    """Tracking home-based phototherapy sessions"""
    EXPOSURE_CHOICES = [
        ('UVB_DEVICE', 'UVB Device'),
        ('SUNLIGHT', 'Natural Sunlight'),
        ('COMBINATION', 'Combined Treatment')
    ]

    plan = models.ForeignKey(
        PhototherapyPlan,
        on_delete=models.CASCADE,
        related_name='home_logs'
    )
    date = models.DateField()
    time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()
    exposure_type = models.CharField(
        max_length=20,
        choices=EXPOSURE_CHOICES,
        default='UVB_DEVICE'
    )
    body_areas_treated = models.TextField()
    notes = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']
        indexes = [models.Index(fields=['plan', 'date'])]

    def __str__(self):
        return f"Home session for {self.plan.patient.get_full_name()} on {self.date}"

class ProblemReport(models.Model):
    """Detailed problem reporting for phototherapy sessions"""
    session = models.ForeignKey(
        PhototherapySession,
        on_delete=models.CASCADE,
        related_name='problem_reports'
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_phototherapy_problems'
    )
    problem_description = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=PhototherapySession.PROBLEM_SEVERITY
    )
    action_taken = models.TextField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    
    # Resolution tracking
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolved_phototherapy_problems'
    )
    resolved_at = models.DateTimeField(null=True)
    
    class Meta:
        ordering = ['-reported_at']
        indexes = [
            models.Index(fields=['session', 'resolved']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"Problem for {self.session} - {self.get_severity_display()}"

    def resolve(self, user, notes):
        """Mark problem as resolved with resolution details"""
        try:
            self.resolved = True
            self.resolution_notes = notes
            self.resolved_by = user
            self.resolved_at = timezone.now()
            self.save()
            logger.info(f"Problem report {self.id} resolved")
        except Exception as e:
            logger.error(f"Failed to resolve problem report {self.id}: {str(e)}")
            raise

class PhototherapyPayment(models.Model):
    """Track payments for phototherapy treatment plans"""
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded')
    ]

    PAYMENT_METHOD = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('OTHER', 'Other')
    ]

    PAYMENT_TYPE = [
        ('FULL', 'Full Payment'),
        ('PER_SESSION', 'Per Session Payment'),
        ('PARTIAL', 'Partial Payment')
    ]

    plan = models.ForeignKey(
        PhototherapyPlan,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    session = models.ForeignKey(
        'PhototherapySession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Associated session if this is a per-session payment"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE,
        default='FULL',
        help_text="Whether this is a full payment or per-session payment"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    payment_date = models.DateTimeField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='PENDING'
    )
    receipt_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_phototherapy_payments'
    )
    
    # For installment tracking
    is_installment = models.BooleanField(
        default=False,
        help_text="Whether this payment is part of an installment plan"
    )
    installment_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Installment number if part of a payment plan"
    )
    total_installments = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of installments planned"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['plan', 'status']),
            models.Index(fields=['receipt_number']),
            models.Index(fields=['session', 'payment_type']),
            models.Index(fields=['is_installment', 'installment_number']),
        ]

    def __str__(self):
        if self.payment_type == 'PER_SESSION':
            return f"Session payment of {self.amount} for {self.plan} - Session {self.session.session_number}"
        return f"Payment of {self.amount} for {self.plan}"

    def clean(self):
        if self.payment_type == 'PER_SESSION' and not self.session:
            raise ValidationError("Session must be specified for per-session payments")
        
        if self.is_installment and (not self.installment_number or not self.total_installments):
            raise ValidationError("Installment number and total installments are required for installment payments")

    @property
    def is_last_installment(self):
        """Check if this is the final installment payment"""
        return self.is_installment and self.installment_number == self.total_installments

    def save(self, *args, **kwargs):
        # Update plan's amount_paid when payment is completed
        if self.status == 'COMPLETED':
            self.plan.amount_paid = self.plan.payments.filter(
                status='COMPLETED'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            # Update billing status based on payments
            if self.plan.amount_paid >= self.plan.total_cost:
                self.plan.billing_status = 'PAID'
            elif self.plan.amount_paid > 0:
                self.plan.billing_status = 'PARTIAL'
            else:
                self.plan.billing_status = 'PENDING'
                
            self.plan.save(update_fields=['amount_paid', 'billing_status'])
            
        super().save(*args, **kwargs)

class PhototherapyReminder(models.Model):
    """Manage reminders for phototherapy sessions and payments"""
    REMINDER_TYPE = [
        ('SESSION', 'Session Reminder'),
        ('PAYMENT', 'Payment Reminder'),
        ('FOLLOWUP', 'Follow-up Reminder'),
        ('MAINTENANCE', 'Device Maintenance')
    ]

    REMINDER_STATUS = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled')
    ]

    plan = models.ForeignKey(
        PhototherapyPlan,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE)
    scheduled_datetime = models.DateTimeField()
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=REMINDER_STATUS,
        default='PENDING'
    )
    sent_at = models.DateTimeField(null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_datetime']
        indexes = [
            models.Index(fields=['plan', 'reminder_type', 'status']),
            models.Index(fields=['scheduled_datetime', 'status']),
        ]

    def __str__(self):
        return f"{self.get_reminder_type_display()} for {self.plan}"

    def mark_as_sent(self):
        """Mark reminder as successfully sent"""
        self.status = 'SENT'
        self.sent_at = timezone.now()
        self.save()

class PhototherapyProgress(models.Model):
    """Track patient progress in phototherapy treatment"""
    plan = models.ForeignKey(
        PhototherapyPlan,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    assessment_date = models.DateField()
    response_level = models.CharField(
        max_length=20,
        choices=[
            ('EXCELLENT', 'Excellent Response'),
            ('GOOD', 'Good Response'),
            ('MODERATE', 'Moderate Response'),
            ('POOR', 'Poor Response'),
            ('NO_RESPONSE', 'No Response')
        ]
    )
    improvement_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Estimated improvement in percentage"
    )
    notes = models.TextField(blank=True)
    side_effects_noted = models.TextField(blank=True)
    next_assessment_date = models.DateField(null=True)
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='phototherapy_assessments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assessment_date']
        indexes = [
            models.Index(fields=['plan', 'assessment_date']),
            models.Index(fields=['response_level']),
        ]

    def __str__(self):
        return f"Progress assessment for {self.plan} on {self.assessment_date}"

class DeviceMaintenance(models.Model):
    """Track maintenance records for phototherapy devices"""
    MAINTENANCE_TYPE = [
        ('ROUTINE', 'Routine Maintenance'),
        ('REPAIR', 'Repair'),
        ('CALIBRATION', 'Calibration'),
        ('INSPECTION', 'Safety Inspection'),
        ('OTHER', 'Other')
    ]

    device = models.ForeignKey(
        PhototherapyDevice,
        on_delete=models.CASCADE,
        related_name='maintenance_records'
    )
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE)
    maintenance_date = models.DateField()
    performed_by = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    next_maintenance_due = models.DateField(null=True)
    parts_replaced = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_maintenance'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-maintenance_date']
        indexes = [
            models.Index(fields=['device', 'maintenance_date']),
            models.Index(fields=['maintenance_type']),
        ]

    def __str__(self):
        return f"{self.get_maintenance_type_display()} for {self.device} on {self.maintenance_date}"

    def schedule_next_maintenance(self):
        """Schedule next maintenance based on maintenance type"""
        if self.maintenance_type == 'ROUTINE':
            self.next_maintenance_due = self.maintenance_date + timedelta(days=90)
        elif self.maintenance_type == 'CALIBRATION':
            self.next_maintenance_due = self.maintenance_date + timedelta(days=180)
        self.save()

class PhototherapyCenter(models.Model):
    """Represents different phototherapy treatment centers/locations"""
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    operating_hours = models.TextField(help_text="Describe the center's operating hours")
    available_devices = models.ManyToManyField(
        PhototherapyDevice,
        related_name='centers',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_available_device_count(self):
        return self.available_devices.filter(is_active=True).count()