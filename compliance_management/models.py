# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model

# Initialize logger and User model
User = get_user_model()
logger = logging.getLogger(__name__)

class ComplianceSchedule(models.Model):
    """Schedule for compliance follow-up calls and monitoring"""
    PRIORITY_CHOICES = [
        ('A', 'Blue A - High Priority'),
        ('B', 'Green B - Medium Priority'),
        ('C', 'Red C - Low Priority'),
    ]

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed'),
        ('RESCHEDULED', 'Rescheduled'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_schedules',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_compliance_schedules',
        limit_choices_to=~models.Q(role__name='PATIENT')
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    actual_date = models.DateField(null=True, blank=True)
    actual_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='B')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    schedule_notes = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    next_follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"Compliance Schedule for {self.patient.get_full_name()} on {self.scheduled_date}"

    def clean(self):
        try:
            if self.actual_date and self.actual_date < self.scheduled_date:
                raise ValidationError("Actual date cannot be earlier than scheduled date")
        except Exception as e:
            logger.error(f"Validation error in ComplianceSchedule: {str(e)}")
            raise

class ComplianceNote(models.Model):
    """Detailed notes about patient compliance and follow-up actions"""
    NOTE_TYPE_CHOICES = [
        ('GENERAL', 'General Note'),
        ('FOLLOW_UP', 'Follow-up Note'),
        ('CONCERN', 'Compliance Concern'),
        ('RESOLUTION', 'Issue Resolution'),
    ]
    schedule = models.ForeignKey(
        ComplianceSchedule,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES
    )
    content = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='compliance_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_private = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['schedule', 'note_type']),
            models.Index(fields=['created_at']),
        ]

class ComplianceIssue(models.Model):
    """Track compliance-related issues and their resolution"""
    SEVERITY_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_issues',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_compliance_issues'
    )
    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolved_compliance_issues'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['severity', 'status']),
        ]

    def __str__(self):
        return f"Compliance Issue - {self.title} ({self.patient.get_full_name()})"

class ComplianceMetric(models.Model):
    """Track and measure patient compliance metrics"""
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_metrics',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    metric_type = models.CharField(
        max_length=20,
        choices=[
            ('MEDICATION', 'Medication Adherence'),
            ('APPOINTMENT', 'Appointment Attendance'),
            ('PHOTOTHERAPY', 'Phototherapy Compliance'),
            ('FOLLOW_UP', 'Follow-up Compliance'),
            ('OVERALL', 'Overall Compliance'),
        ]
    )
    evaluation_date = models.DateField()
    compliance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    evaluation_period_start = models.DateField()
    evaluation_period_end = models.DateField()
    notes = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='evaluated_compliance_metrics'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['patient', 'metric_type', 'evaluation_date']),
        ]

    def clean(self):
        if self.evaluation_period_end < self.evaluation_period_start:
            raise ValidationError("Evaluation end date cannot be earlier than start date")

class ComplianceReminder(models.Model):
    """Automated reminders for compliance-related activities"""
    REMINDER_TYPE_CHOICES = [
        ('MEDICATION', 'Medication Reminder'),
        ('APPOINTMENT', 'Appointment Reminder'),
        ('FOLLOW_UP', 'Follow-up Call Reminder'),
        ('PHOTOTHERAPY', 'Phototherapy Session Reminder'),
        ('GENERAL', 'General Reminder'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_reminders',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    scheduled_datetime = models.DateTimeField()
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_datetime']
        indexes = [
            models.Index(fields=['patient', 'reminder_type', 'status']),
            models.Index(fields=['scheduled_datetime', 'status']),
        ]

    def clean(self):
        try:
            if self.scheduled_datetime < timezone.now():
                raise ValidationError("Scheduled datetime cannot be in the past")
        except Exception as e:
            logger.error(f"Validation error in ComplianceReminder: {str(e)}")
            raise

class ComplianceReport(models.Model):
    """Generate and store compliance reports"""
    REPORT_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual Patient Report'),
        ('GROUP', 'Patient Group Report'),
        ('SUMMARY', 'Summary Report'),
        ('TREND', 'Trend Analysis'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    parameters = models.JSONField(default=dict)
    results = models.JSONField()
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_compliance_reports'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField()
    period_end = models.DateField()
    file_path = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['report_type', 'generated_at']),
            models.Index(fields=['period_start', 'period_end']),
        ]

    def clean(self):
        if self.period_end < self.period_start:
            raise ValidationError("Report period end date cannot be earlier than start date")

class PatientGroup(models.Model):
    """Group patients for targeted compliance monitoring"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    patients = models.ManyToManyField(
        User,
        related_name='compliance_groups',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    criteria = models.JSONField(
        help_text="Criteria used for grouping patients"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_patient_groups'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def __str__(self):
        return self.name

class ComplianceAlert(models.Model):
    """Automated alerts for compliance-related issues"""
    ALERT_TYPE_CHOICES = [
        ('MISSED_APPOINTMENT', 'Missed Appointment'),
        ('LOW_COMPLIANCE', 'Low Compliance Score'),
        ('MISSED_MEDICATION', 'Missed Medication'),
        ('FOLLOW_UP_NEEDED', 'Follow-up Required'),
        ('CRITICAL_ISSUE', 'Critical Issue'),
    ]

    SEVERITY_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_alerts',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolved_compliance_alerts'
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'alert_type', 'is_resolved']),
            models.Index(fields=['severity', 'is_resolved']),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.patient.get_full_name()}"