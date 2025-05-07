from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class ErrorLog(models.Model):
    ERROR_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=ERROR_LEVELS)
    message = models.TextField()
    traceback = models.TextField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    url = models.URLField(max_length=255, blank=True, null=True)
    method = models.CharField(max_length=10, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.level} at {self.timestamp}: {self.message[:50]}..."

    class Meta:
        ordering = ['-timestamp']