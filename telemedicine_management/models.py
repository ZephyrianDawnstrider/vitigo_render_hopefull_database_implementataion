from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class TeleconsultationSession(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='teleconsultations',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teleconsultations_conducted')
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    video_call_link = models.URLField()
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Teleconsultation: {self.patient.user.get_full_name()} with Dr. {self.doctor.get_full_name()} on {self.scheduled_start}"

class TeleconsultationPrescription(models.Model):
    teleconsultation = models.OneToOneField(TeleconsultationSession, on_delete=models.CASCADE, related_name='prescription')
    prescription_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription for {self.teleconsultation}"

class TeleconsultationFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('LAB_RESULT', 'Lab Result'),
        ('MEDICAL_RECORD', 'Medical Record'),
        ('PRESCRIPTION', 'Prescription'),
        ('OTHER', 'Other'),
    ]

    teleconsultation = models.ForeignKey(TeleconsultationSession, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='teleconsultation_files/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_file_type_display()} for {self.teleconsultation}"

class TeleconsultationFeedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    teleconsultation = models.OneToOneField(TeleconsultationSession, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.teleconsultation}"

class TelemedicinevirtualWaitingRoom(models.Model):
    patient = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='virtual_waiting_room',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    teleconsultation = models.ForeignKey(TeleconsultationSession, on_delete=models.CASCADE, related_name='waiting_room_entries')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.patient.get_full_name()} in waiting room for {self.teleconsultation}"