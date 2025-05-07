from django.db import models
from django.conf import settings
from django.db.models import JSONField
from django.contrib.auth import get_user_model
from access_control.models import Module

User = get_user_model()

class ReportCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='report_categories')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Report(models.Model):
    category = models.ForeignKey(ReportCategory, on_delete=models.CASCADE, related_name='reports')
    name = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
class ReportExport(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'), 
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='exports')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    export_file = models.FileField(upload_to='report_exports/', null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report.name} Export ({self.start_date.date()} to {self.end_date.date()})"