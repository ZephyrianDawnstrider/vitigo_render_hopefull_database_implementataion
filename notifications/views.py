# Standard library imports
import logging

# Django core imports
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.contrib import messages

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    UserNotification,
    SystemActivityLog,
    UserActivityLog,
    EmailNotification,
    SMSNotification,
    PushNotification
)

# Logger configuration
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module='notification_management'):
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

class NotificationManagementView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'notification_management'):
            messages.error(request, "You don't have permission to access Notifications")
            return handler403(request, exception="You don't have permission to access notifications")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('notification_dashboard.html', self.request.user.role)

    def get(self, request):
        try:
            # Get all notifications and logs with proper error handling
            context = {}
            
            # Get user notifications with pagination
            try:
                user_notifications = UserNotification.objects.all()
                paginator = Paginator(user_notifications, 10)
                page = request.GET.get('page')
                try:
                    user_notifications = paginator.page(page)
                except PageNotAnInteger:
                    user_notifications = paginator.page(1)
                except EmptyPage:
                    user_notifications = paginator.page(paginator.num_pages)
                context['user_notifications'] = user_notifications
                context['paginator'] = paginator
                context['page_obj'] = user_notifications
            except Exception as e:
                logger.error(f"Error fetching user notifications: {str(e)}")
                return handler500(request, exception="Error fetching notifications")

            # Get other notification types and logs
            try:
                context.update({
                    'system_activity_logs': SystemActivityLog.objects.all(),
                    'user_activity_logs': UserActivityLog.objects.all(),
                    'email_notifications': EmailNotification.objects.all(),
                    'sms_notifications': SMSNotification.objects.all(),
                    'push_notifications': PushNotification.objects.all(),
                })
            except Exception as e:
                logger.error(f"Error fetching notification logs: {str(e)}")
                messages.error(request, "Error fetching notification logs")
                return handler500(request, exception="Error fetching notification logs")

            # Calculate statistics
            try:
                context.update({
                    'total_user_notifications': UserNotification.objects.count(),
                    'total_system_activity_logs': SystemActivityLog.objects.count(),
                    'total_user_activity_logs': UserActivityLog.objects.count(),
                    'total_email_notifications': EmailNotification.objects.count(),
                    'total_sms_notifications': SMSNotification.objects.count(),
                    'total_push_notifications': PushNotification.objects.count(),
                })
            except Exception as e:
                logger.error(f"Error calculating notification statistics: {str(e)}")
                messages.error(request, "Error calculating statistics")
                return handler500(request, exception="Error calculating statistics")

            # Add user role to context
            context['user_role'] = request.user.role

            return render(request, self.get_template_name(), context)

        except Exception as e:
            logger.exception(f"Unexpected error in notification management: {str(e)}")
            messages.error(request, "Unexpected error in notification management")
            return handler500(request, exception=str(e))