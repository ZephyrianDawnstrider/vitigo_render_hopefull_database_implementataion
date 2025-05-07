# notifications/management/commands/populate_notifications.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from notifications.models import (
    NotificationType, UserNotification, SystemActivityLog, UserActivityLog, EmailNotification, SMSNotification, PushNotification
)

class Command(BaseCommand):
    help = 'Generate sample notifications data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample notifications data...')

        # Create sample notification types if they don't exist
        notification_types = [
            {'name': 'Appointment Reminder', 'description': 'Reminder for upcoming appointments'},
            {'name': 'System Alert', 'description': 'Important system alerts'},
            {'name': 'Message', 'description': 'Messages from the clinic'},
        ]
        for nt in notification_types:
            NotificationType.objects.get_or_create(
                name=nt['name'],
                defaults={'description': nt['description']}
            )

        # Fetch all users and notification types
        users = CustomUser.objects.all()
        notification_types = NotificationType.objects.all()

        # Create sample user notifications
        for user in users:
            for _ in range(random.randint(1, 5)):  # Generate 1 to 5 notifications per user
                notification_type = random.choice(notification_types)
                UserNotification.objects.create(
                    user=user,
                    notification_type=notification_type,
                    message=f"Sample message for {notification_type.name}",
                    is_read=random.choice([True, False]),
                    read_at=timezone.now() if random.choice([True, False]) else None
                )

        # Create sample system activity logs
        for _ in range(20):  # Generate 20 sample system activity logs
            SystemActivityLog.objects.create(
                user=random.choice(users) if random.choice([True, False]) else None,
                action='Sample system action',
                details={'key': 'value'},
                timestamp=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
            )

        # Create sample user activity logs
        for user in users:
            for _ in range(random.randint(1, 5)):  # Generate 1 to 5 activity logs per user
                UserActivityLog.objects.create(
                    user=user,
                    action='Sample user action',
                    details={'key': 'value'},
                    timestamp=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
                )

        # Create sample email notifications
        for user in users:
            for _ in range(random.randint(1, 3)):  # Generate 1 to 3 email notifications per user
                EmailNotification.objects.create(
                    user=user,
                    subject='Sample Email Subject',
                    message='Sample email message',
                    status=random.choice(['SENT', 'FAILED', 'PENDING'])
                )

        # Create sample SMS notifications
        for user in users:
            for _ in range(random.randint(1, 3)):  # Generate 1 to 3 SMS notifications per user
                SMSNotification.objects.create(
                    user=user,
                    phone_number=f"+1234567890{random.randint(0, 9)}",
                    message='Sample SMS message',
                    status=random.choice(['SENT', 'FAILED', 'PENDING'])
                )

        # Create sample push notifications
        for user in users:
            for _ in range(random.randint(1, 3)):  # Generate 1 to 3 push notifications per user
                PushNotification.objects.create(
                    user=user,
                    title='Sample Push Notification Title',
                    message='Sample push notification message',
                    status=random.choice(['SENT', 'FAILED', 'PENDING'])
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample notifications data'))