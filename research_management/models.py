from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class ResearchStudy(models.Model):
    STUDY_STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    principal_investigator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='led_studies')
    status = models.CharField(max_length=20, choices=STUDY_STATUS_CHOICES, default='PLANNING')
    ethics_approval_document = models.FileField(upload_to='research_documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Research Studies"

class StudyProtocol(models.Model):
    study = models.OneToOneField(ResearchStudy, on_delete=models.CASCADE, related_name='protocol')
    version = models.CharField(max_length=20)
    document = models.FileField(upload_to='study_protocols/')
    approved_date = models.DateField()

    def __str__(self):
        return f"Protocol for {self.study.title} (v{self.version})"

class PatientStudyEnrollment(models.Model):
    ENROLLMENT_STATUS_CHOICES = [
        ('SCREENING', 'Screening'),
        ('ENROLLED', 'Enrolled'),
        ('COMPLETED', 'Completed'),
        ('WITHDRAWN', 'Withdrawn'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='study_enrollments',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='patient_enrollments')
    enrollment_date = models.DateField()
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default='SCREENING')
    withdrawal_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.patient.user.get_full_name()} in {self.study.title}"

class DataCollectionPoint(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='data_collection_points')
    name = models.CharField(max_length=100)
    description = models.TextField()
    target_date = models.DurationField(help_text="Time from enrollment date")

    def __str__(self):
        return f"{self.name} for {self.study.title}"

class ResearchData(models.Model):
    enrollment = models.ForeignKey(PatientStudyEnrollment, on_delete=models.CASCADE, related_name='research_data')
    collection_point = models.ForeignKey(DataCollectionPoint, on_delete=models.CASCADE)
    collected_date = models.DateField()
    data = models.JSONField()
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Data for {self.enrollment} at {self.collection_point.name}"

class AnalysisResult(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='analysis_results')
    title = models.CharField(max_length=255)
    description = models.TextField()
    result_data = models.JSONField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis: {self.title} for {self.study.title}"

class Publication(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=255)
    authors = models.TextField()
    journal = models.CharField(max_length=255)
    publication_date = models.DateField()
    doi = models.CharField(max_length=100, blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title