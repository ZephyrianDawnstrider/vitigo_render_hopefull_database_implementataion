# webhooks/models.py
from django.db import models
from django.contrib.auth import get_user_model

class WhatsAppWebhook(models.Model):
    CONVERSATION_STATES = [
        ('MENU', 'Main Menu'),
        ('NEW_QUERY', 'Creating New Query'),
        ('VIEW_QUERIES', 'Viewing Queries'),
        ('AWAITING_SUBJECT', 'Waiting for Subject'),
        ('AWAITING_DESCRIPTION', 'Waiting for Description'),
    ]

    message_id = models.CharField(max_length=255, unique=True)
    from_number = models.CharField(max_length=20)
    message_body = models.TextField()
    timestamp = models.DateTimeField()
    media_url = models.URLField(blank=True, null=True)
    media_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    conversation_state = models.CharField(
        max_length=20, 
        choices=CONVERSATION_STATES,
        default='MENU'
    )
    temp_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL,
        null=True, blank=True
    )


class FacebookMessengerWebhook(models.Model):
    CONVERSATION_STATES = [
        ('MENU', 'Main Menu'),
        ('NEW_QUERY', 'Creating New Query'),
        ('VIEW_QUERIES', 'Viewing Queries'),
        ('AWAITING_SUBJECT', 'Waiting for Subject'),
        ('AWAITING_DESCRIPTION', 'Waiting for Description'),
    ]

    psid = models.CharField(max_length=255)  # Page-scoped ID
    message_id = models.CharField(max_length=255, unique=True)
    message_body = models.TextField()
    timestamp = models.DateTimeField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    conversation_state = models.CharField(
        max_length=20, 
        choices=CONVERSATION_STATES,
        default='MENU'
    )
    temp_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        verbose_name = 'Facebook Messenger Webhook'
        verbose_name_plural = 'Facebook Messenger Webhooks'


class InstagramWebhook(models.Model):
    CONVERSATION_STATES = [
        ('MENU', 'Main Menu'),
        ('NEW_QUERY', 'Creating New Query'),
        ('VIEW_QUERIES', 'Viewing Queries'),
        ('AWAITING_SUBJECT', 'Waiting for Subject'),
        ('AWAITING_DESCRIPTION', 'Waiting for Description'),
    ]

    igsid = models.CharField(max_length=255) 
    message_id = models.CharField(max_length=255, unique=True)
    message_body = models.TextField()
    message_type = models.CharField(max_length=50)
    media_url = models.URLField(blank=True, null=True)
    timestamp = models.DateTimeField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    conversation_state = models.CharField(
        max_length=20, 
        choices=CONVERSATION_STATES,
        default='MENU'
    )
    temp_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        verbose_name = 'Instagram Webhook'
        verbose_name_plural = 'Instagram Webhooks'