# Standard library imports
import logging
from datetime import datetime

# Django imports
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Local application imports

# Initialize commonly used variables
User = get_user_model()
logger = logging.getLogger(__name__)

class VisitStatus(models.Model):
    """Configurable status options for clinic visits"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_terminal_state = models.BooleanField(
        default=False,
        help_text="Whether this status represents an end state (e.g., Completed, Cancelled)"
    )
    color_code = models.CharField(
        max_length=7,
        default="#000000",
        help_text="Hex color code for status display"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'display_name']
        verbose_name = 'Visit Status'
        verbose_name_plural = 'Visit Statuses'

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving VisitStatus: {str(e)}")
            raise

class ClinicVisit(models.Model):
    """Tracks patient visits and their flow through the clinic"""
    PRIORITY_CHOICES = [
        ('A', 'Blue A - High Priority'),
        ('B', 'Green B - Medium Priority'),
        ('C', 'Red C - Low Priority'),
    ]

    # Basic Information
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='clinic_visits',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    visit_date = models.DateField(default=timezone.now)
    visit_number = models.CharField(max_length=20, unique=True)  # Auto-generated
    priority = models.CharField(
        max_length=1,
        choices=PRIORITY_CHOICES,
        default='B'
    )
    
    # Visit Status
    current_status = models.ForeignKey(
        VisitStatus,
        on_delete=models.PROTECT,
        related_name='visits'
    )
    registration_time = models.DateTimeField(auto_now_add=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_visits'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-visit_date', '-registration_time']
        indexes = [
            models.Index(fields=['visit_date']),
            models.Index(fields=['visit_number']),
        ]

    def __str__(self):
        return f"Visit {self.visit_number} - {self.patient.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.visit_number:
            # Generate visit number format: VN-YYYYMMDD-XXXX
            date_str = timezone.now().strftime('%Y%m%d')
            last_visit = ClinicVisit.objects.filter(
                visit_number__startswith=f'VN-{date_str}'
            ).order_by('visit_number').last()
            
            if last_visit:
                last_num = int(last_visit.visit_number.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            
            self.visit_number = f'VN-{date_str}-{new_num}'
        
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving ClinicVisit: {str(e)}")
            raise

class VisitStatusLog(models.Model):
    """Tracks status changes during a clinic visit"""
    visit = models.ForeignKey(
        ClinicVisit,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    status = models.ForeignKey(
        VisitStatus,
        on_delete=models.PROTECT
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.visit.visit_number} - {self.status.display_name}"


class ClinicChecklist(models.Model):
    """Configurable checklists for different clinic processes"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class ChecklistItem(models.Model):
    """Individual items within a checklist"""
    checklist = models.ForeignKey(
        ClinicChecklist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    description = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    help_text = models.TextField(blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.checklist.name} - {self.description}"

class VisitChecklist(models.Model):
    """Tracks completion of checklist items for each visit"""
    visit = models.ForeignKey(
        ClinicVisit,
        on_delete=models.CASCADE,
        related_name='checklists'
    )
    checklist = models.ForeignKey(
        ClinicChecklist,
        on_delete=models.CASCADE
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['visit', 'checklist']

    def __str__(self):
        return f"{self.visit.visit_number} - {self.checklist.name}"

class VisitChecklistItem(models.Model):
    """Status of individual checklist items for a visit"""
    visit_checklist = models.ForeignKey(
        VisitChecklist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    checklist_item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.CASCADE
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
        unique_together = ['visit_checklist', 'checklist_item']

    def __str__(self):
        return f"{self.visit_checklist} - {self.checklist_item.description}"