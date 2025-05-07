from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.template.defaultfilters import register
import os

User = get_user_model()

class Query(models.Model):
    PRIORITY_CHOICES = [
        ('A', 'High'),
        ('B', 'Medium'),
        ('C', 'Low'),
    ]
    SOURCE_CHOICES = [
        ('WEBSITE', 'Website'),
        ('CHATBOT', 'Chatbot'),
        ('SOCIAL_MEDIA', 'Social Media'),
        ('PHONE', 'Phone Call'),
        ('IVR', 'Interactive Voice Response'),
        ('EMAIL', 'Email'),
        ('WALK_IN', 'Walk-in'),
        ('MOBILE_APP', 'Mobile App'),
    ]
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('IN_PROGRESS', 'In Progress'),
        ('WAITING', 'Waiting for Response'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    QUERY_TYPE_CHOICES = [
        ('GENERAL', 'General Inquiry'),
        ('APPOINTMENT', 'Appointment Related'),
        ('TREATMENT', 'Treatment Related'),
        ('BILLING', 'Billing Related'),
        ('COMPLAINT', 'Complaint'),
        ('FEEDBACK', 'Feedback'),
        ('OTHER', 'Other'),
    ]

    # Existing fields
    query_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='queries')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='assigned_queries')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='B')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    tags = models.ManyToManyField('QueryTag', blank=True)

    # New fields (all with null=True, blank=True for backward compatibility)
    query_type = models.CharField(max_length=20, choices=QUERY_TYPE_CHOICES, null=True, blank=True)
    expected_response_date = models.DateTimeField(null=True, blank=True)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    is_patient = models.BooleanField(null=True, blank=True)
    conversion_status = models.BooleanField(null=True, blank=True, help_text="Whether query led to appointment/conversion")
    resolution_summary = models.TextField(null=True, blank=True)
    response_time = models.DurationField(null=True, blank=True)
    satisfaction_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Query")
        verbose_name_plural = _("Queries")

    def __str__(self):
        return f"Query {self.query_id}: {self.subject}"


class QueryUpdate(models.Model):
    query = models.ForeignKey(Query, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update for Query {self.query.query_id} at {self.created_at}"


class QueryTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class QueryAttachment(models.Model):
    query = models.ForeignKey(Query, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='query_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for Query {self.query.query_id}"
    

