
from django.db import transaction
from django.utils import timezone
import logging

from .models import UserNotification, EmailNotification, SMSNotification

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notifications(user, notification_type, message, send_email=False, send_sms=False, phone_number=None):
        """
        Creates notifications based on the specified parameters.
        Returns a tuple of (success, error_message)
        """
        try:
            # Create user notification
            UserNotification.objects.create(
                user=user,
                notification_type=notification_type,
                message=message
            )

            # Create email notification if requested
            if send_email:
                EmailNotification.objects.create(
                    user=user,
                    subject=f"{notification_type.name} Notification",
                    message=message,
                    status='PENDING'
                )

            # Create SMS notification if requested and phone number is provided
            if send_sms and phone_number:
                SMSNotification.objects.create(
                    user=user,
                    phone_number=phone_number,
                    message=message,
                    status='PENDING'
                )

            return True, None

        except Exception as e:
            logger.error(f"Failed to create notifications: {str(e)}")
            return False, str(e)