from django.core.mail import send_mail, get_connection, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from notifications.models import UserNotification, EmailNotification, NotificationType
from django.utils import timezone
import logging
from access_control.models import Role

logger = logging.getLogger('query_management')

def send_query_notification(query, notification_type, recipient=None, **kwargs):
    """Send notifications for query events"""
    try:
        if recipient is None:
            recipient = query.assigned_to or query.user

        if not recipient:
            logger.warning(f"No recipient found for query #{query.query_id}")
            return

        # Log notification attempt
        logger.info(f"Preparing notification for query #{query.query_id}, type: {notification_type}")

        # Map notification types to NotificationType names
        notification_type_mapping = {
            'created': 'QUERY_CREATED',
            'assigned': 'QUERY_ASSIGNED',
            'status_updated': 'QUERY_STATUS_UPDATED',
            'resolved': 'QUERY_RESOLVED',
        }

        # Get or create the NotificationType instance
        notification_type_obj, created = NotificationType.objects.get_or_create(
            name=notification_type_mapping.get(notification_type, 'QUERY_STATUS_UPDATED'),
            defaults={
                'description': f'Notification for {notification_type} query event'
            }
        )
        
        if created:
            logger.info(f"Created new NotificationType: {notification_type_obj.name}")

        # Create notification message
        notification_messages = {
            'created': f'New query #{query.query_id} has been created: {query.subject}',
            'assigned': f'Query #{query.query_id} has been assigned to you',
            'status_updated': f'Status updated for query #{query.query_id}: {query.status}',
            'resolved': f'Query #{query.query_id} has been resolved',
        }

        message = notification_messages.get(notification_type, '')
        
        # Create the notification with proper notification type
        UserNotification.objects.create(
            user=recipient,
            notification_type=notification_type_obj,
            message=message
        )

        # Email notification setup
        email_subjects = {
            'created': f'New Query Created - #{query.query_id}',
            'assigned': f'Query Assigned - #{query.query_id}',
            'status_updated': f'Query Status Updated - #{query.query_id}',
            'resolved': f'Query Resolved - #{query.query_id}',
        }

        subject = email_subjects.get(notification_type, '')
        email_template = f'query_{notification_type}_email.html'
        
        # Log template selection
        logger.debug(f"Using email template: {email_template}")

        # Get any new attachments from kwargs or query
        attachments = kwargs.get('attachments', None)
        if not attachments and hasattr(query, 'attachments'):
            attachments = query.attachments.all()

        try:
            html_message = render_to_string(email_template, {
                'query': query,
                'recipient': recipient,
                'attachments': attachments,
                **kwargs
            })
            logger.debug("Email template rendered successfully")

            # Always try to send real email regardless of DEBUG mode
            logger.info(f"Attempting to send email to {recipient.email}")
            
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                fail_silently=False,
            )
            
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email],
                connection=connection
            )
            email.content_subtype = "html"  # Main content is now text/html
            
            # Attach files if present
            if attachments:
                for attachment in attachments:
                    try:
                        email.attach_file(attachment.file.path)
                    except Exception as e:
                        logger.error(f"Failed to attach file {attachment.file.name}: {str(e)}")
            
            # Send email
            email_sent = email.send(fail_silently=False)
            
            logger.info(f"Email sent successfully: {email_sent}")
            
            # Log email notification
            EmailNotification.objects.create(
                user=recipient,
                subject=subject,
                message=html_message,
                status='SENT' if email_sent else 'FAILED',
                sent_at=timezone.now()
            )

        except Exception as e:
            logger.error(f"Email error: {str(e)}")
            logger.error(f"Email settings: HOST={settings.EMAIL_HOST}, "
                        f"PORT={settings.EMAIL_PORT}, "
                        f"USER={settings.EMAIL_HOST_USER}, "
                        f"TLS={settings.EMAIL_USE_TLS}")
            
            EmailNotification.objects.create(
                user=recipient,
                subject=subject,
                message=f"Error sending email: {str(e)}",
                status='FAILED',
                sent_at=timezone.now()
            )
            raise  # Re-raise the exception to see it in the logs

    except Exception as e:
        logger.exception(f"General notification error: {str(e)}")
        raise  # Re-raise to see the error in development


def get_template_path(base_template, role, module=''):
    """
    Resolves template path based on user role.
    Now uses the template_folder from Role model.
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        # Fallback for any legacy code
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    if module:
        return f'{role_folder}/{module}/{base_template}'
    return f'{role_folder}/{base_template}'