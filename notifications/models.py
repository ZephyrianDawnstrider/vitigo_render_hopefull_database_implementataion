from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE, related_name='user_notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.email} - {self.message[:20]}"

class SystemActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email if self.user else 'System'} - {self.action} at {self.timestamp}"

class UserActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.timestamp}"

class EmailNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_notifications')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ], default='PENDING')

    def __str__(self):
        return f"Email to {self.user.email} - {self.subject[:20]}"

class SMSNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_notifications')
    phone_number = models.CharField(max_length=15)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ], default='PENDING')

    def __str__(self):
        return f"SMS to {self.phone_number} - {self.message[:20]}"

class PushNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ], default='PENDING')

    def __str__(self):
        return f"Push notification to {self.user.email} - {self.title[:20]}"