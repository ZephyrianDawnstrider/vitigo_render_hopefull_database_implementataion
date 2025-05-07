from django.contrib import admin
from .models import (
    NotificationType, UserNotification, SystemActivityLog,
    UserActivityLog, EmailNotification, SMSNotification,
    PushNotification
)

@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message', 'is_read', 'created_at', 'read_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('user__email', 'message')
    date_hierarchy = 'created_at'

@admin.register(SystemActivityLog)
class SystemActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'action', 'details')
    date_hierarchy = 'timestamp'

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'action', 'details')
    date_hierarchy = 'timestamp'

@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('user__email', 'subject', 'message')
    date_hierarchy = 'sent_at'

@admin.register(SMSNotification)
class SMSNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'message', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('user__email', 'phone_number', 'message')
    date_hierarchy = 'sent_at'

@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('user__email', 'title', 'message')
    date_hierarchy = 'sent_at'
