# Standard library imports
import logging

# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Custom variables
User = get_user_model()
logger = logging.getLogger(__name__)


class TimeSlotConfig(models.Model):
    """Configuration for clinic's standard time slots"""
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.start_time} - {self.end_time} ({self.duration} mins)"

    class Meta:
        ordering = ['start_time']

class Center(models.Model):
    """Medical centers/clinic locations"""
    name = models.CharField(max_length=100)
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class DoctorTimeSlot(models.Model):
    """Available time slots for each doctor"""
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='time_slots',
        limit_choices_to={'role__name': 'DOCTOR'}
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='doctor_time_slots'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('doctor', 'center', 'date', 'start_time')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"


class Appointment(models.Model):
    APPOINTMENT_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('FOLLOW_UP', 'Follow-up'),
        ('PROCEDURE', 'Procedure'),
        ('PHOTOTHERAPY', 'Phototherapy'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
    ]

    PRIORITY_CHOICES = [
        ('A', 'High'),
        ('B', 'Medium'),
        ('C', 'Low'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='appointments',
        limit_choices_to={'role__name': 'PATIENT'}  
    )
    doctor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='doctor_appointments',
        limit_choices_to={'role__name': 'DOCTOR'}   
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='appointments',
        blank = True,
        null = True
    )
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES, default='CONSULTATION')
    date = models.DateField()
    time_slot = models.ForeignKey(DoctorTimeSlot, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='B')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ensure the time slot belongs to the correct center
        if self.time_slot and self.center != self.time_slot.center:
            raise ValidationError("The selected time slot is not available at this center")
            
        if self.appointment_type == 'FOLLOW_UP':
            days_until_appointment = (self.date - timezone.now().date()).days
            if days_until_appointment > 30:
                raise ValidationError("Follow-up appointments cannot be scheduled more than 30 days in advance")

    def __str__(self):
        return f"Appointment for {self.patient} on {self.date} at {self.time_slot}"

    def can_acknowledge(self, user):
        """Check if the user can acknowledge this appointment"""
        if self.status != 'CONFIRMED':
            return False

        # Check if user hasn't already acknowledged
        return not self.acknowledgements.filter(user=user).exists()

    @property
    def is_fully_acknowledged(self):
        """Check if both parties have acknowledged the appointment"""
        patient_ack = self.acknowledgements.filter(user__role__name='PATIENT').exists()
        staff_ack = self.acknowledgements.filter(~Q(user__role__name='PATIENT')).exists()
        return patient_ack and staff_ack

    def get_patient_acknowledgement(self):
        """Get patient's acknowledgement if exists"""
        return self.acknowledgements.filter(user__role__name='PATIENT').first()

    def get_staff_acknowledgement(self):
        """Get staff's acknowledgement if exists"""
        return self.acknowledgements.filter(~Q(user__role__name='PATIENT')).first()


class ReminderTemplate(models.Model):
    """Pre-configured reminder templates"""
    name = models.CharField(max_length=100)
    days_before = models.PositiveIntegerField(
        help_text="Days before appointment to send reminder"
    )
    hours_before = models.PositiveIntegerField(
        help_text="Hours before appointment to send reminder",
        default=0
    )
    message_template = models.TextField(
        help_text="Use {patient}, {doctor}, {date}, {time}, {type} as placeholders"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.name} - {self.days_before}d {self.hours_before}h before"

    class Meta:
        ordering = ['days_before', 'hours_before']
        indexes = [
            models.Index(fields=['is_active', 'days_before']),
        ]

class ReminderConfiguration(models.Model):
    """Configure which reminders to send for different appointment types"""
    appointment_type = models.CharField(
        max_length=20,
        choices=Appointment.APPOINTMENT_TYPES,
        unique=True
    )
    templates = models.ManyToManyField(
        ReminderTemplate,
        related_name='configurations'
    )
    reminder_types = models.JSONField(
        default=dict,
        help_text="Configure email/SMS options for each template"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reminders for {self.get_appointment_type_display()}"


class AppointmentReminder(models.Model):
    REMINDER_TYPES = [
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('BOTH', 'Both SMS and Email'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]

    appointment = models.ForeignKey(
        'Appointment', 
        on_delete=models.CASCADE, 
        related_name='reminders'
    )
    reminder_type = models.CharField(
        max_length=5,
        choices=REMINDER_TYPES,
        default='BOTH'
    )
    reminder_date = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reminders'
    )
    template = models.ForeignKey(
        ReminderTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointment_reminders'
    )

    class Meta:
        ordering = ['reminder_date']
        indexes = [
            models.Index(fields=['reminder_date', 'status']),
            models.Index(fields=['appointment', 'status']),
        ]

    def __str__(self):
        return f"Reminder for {self.appointment} at {self.reminder_date}"

    def clean(self):
        if self.reminder_date:
            # Don't allow reminders in the past
            if self.reminder_date < timezone.now():
                raise ValidationError("Reminder date cannot be in the past")
            
            # Don't allow reminders after the appointment
            if self.reminder_date > self.appointment.date:
                raise ValidationError("Reminder cannot be scheduled after the appointment")
            
            # Don't allow too many reminders
            if self.appointment.reminders.count() >= 5:
                raise ValidationError("Maximum 5 reminders allowed per appointment")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def mark_as_sent(self):
        """Mark reminder as sent"""
        try:
            self.sent = True
            self.status = 'SENT'
            self.sent_at = timezone.now()
            self.save()
            logger.info(f"Reminder {self.id} marked as sent successfully")
        except Exception as e:
            logger.error(f"Error marking reminder {self.id} as sent: {str(e)}")
            raise

    def mark_as_failed(self, reason):
        """Mark reminder as failed with reason"""
        try:
            self.status = 'FAILED'
            self.failure_reason = reason
            self.save()
            logger.info(f"Reminder {self.id} marked as failed: {reason}")
        except Exception as e:
            logger.error(f"Error marking reminder {self.id} as failed: {str(e)}")
            raise


class CancellationReason(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='cancellation_reason')
    reason = models.TextField()
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation reason for {self.appointment}"


class AppointmentAcknowledgement(models.Model):
    """Track acknowledgements for appointments"""
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='acknowledgements'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='appointment_acknowledgements'
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('appointment', 'user')
        ordering = ['acknowledged_at']

    def __str__(self):
        return f"Acknowledgement by {self.user} for {self.appointment}"

    def clean(self):
        if self.appointment.acknowledgements.filter(user=self.user).exists():
            raise ValidationError("User has already acknowledged this appointment")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
        # After saving, check if both patient and any staff member have acknowledged
        patient_ack = self.appointment.acknowledgements.filter(
            user__role__name='PATIENT'
        ).exists()
        staff_ack = self.appointment.acknowledgements.filter(
            ~Q(user__role__name='PATIENT')  # Any user who is not a patient
        ).exists()
        
        # If both patient and staff have acknowledged, update appointment status to CONFIRMED
        if patient_ack and staff_ack:
            self.appointment.status = 'CONFIRMED'
            self.appointment.save(update_fields=['status'])