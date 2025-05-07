# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.urls import reverse

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from ..models import MaintenanceSchedule
from ..utils import get_template_path
from ..forms import MaintenanceScheduleForm

# Initialize logger
logger = logging.getLogger(__name__)

class MaintenanceScheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def get_template_name(self):
        return get_template_path('maintenance/maintenance_schedule.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            # Get filter parameters
            search_query = request.GET.get('search', '')
            status = request.GET.get('status', '')
            priority = request.GET.get('priority', '')
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')

            # Base queryset
            schedules = MaintenanceSchedule.objects.select_related('asset').order_by('scheduled_date')

            # Apply filters
            if search_query:
                schedules = schedules.filter(
                    Q(asset__name__icontains=search_query) |
                    Q(asset__asset_id__icontains=search_query) |
                    Q(maintenance_type__icontains=search_query)
                )
            if status:
                schedules = schedules.filter(status=status)
            if priority:
                schedules = schedules.filter(priority=priority)
            if date_from:
                schedules = schedules.filter(scheduled_date__gte=date_from)
            if date_to:
                schedules = schedules.filter(scheduled_date__lte=date_to)  # Fixed missing parenthesis

            # Pagination
            page = request.GET.get('page', 1)
            paginator = Paginator(schedules, 10)
            try:
                schedules = paginator.page(page)
            except PageNotAnInteger:
                schedules = paginator.page(1)
            except EmptyPage:
                schedules = paginator.page(paginator.num_pages)

            context = {
                'schedules': schedules,
                'search_query': search_query,
                'selected_status': status,
                'selected_priority': priority,
                'date_from': date_from,
                'date_to': date_to,
                'status_choices': MaintenanceSchedule.STATUS_CHOICES,
                'priority_choices': MaintenanceSchedule.PRIORITY_CHOICES,
                'has_filters': bool(search_query or status or priority or date_from or date_to),
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in maintenance schedule view: {str(e)}")
            messages.error(request, "An error occurred while loading maintenance schedules")
            return redirect('asset_dashboard')

class CreateMaintenanceScheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to schedule maintenance")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('maintenance/maintenance_schedule_form.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            form = MaintenanceScheduleForm()
            context = {
                'form': form,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': 'Schedule Maintenance'
            }
            return render(request, template_path, context)
        except Exception as e:
            logger.exception(f"Error in CreateMaintenanceScheduleView GET: {str(e)}")
            messages.error(request, "An error occurred while loading the maintenance form.")
            return handler500(request, exception=str(e))

    def post(self, request):
        try:
            form = MaintenanceScheduleForm(request.POST)
            if form.is_valid():
                maintenance = form.save()
                messages.success(request, "Maintenance scheduled successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Maintenance scheduled successfully',
                    'redirect_url': reverse('maintenance_schedule')
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
            
        except Exception as e:
            logger.exception(f"Error in CreateMaintenanceScheduleView POST: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to schedule maintenance'
            }, status=500)

class EditMaintenanceScheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to edit maintenance schedules")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('maintenance/edit_maintenance.html', self.request.user.role, 'asset_management')

    def get(self, request, schedule_id):
        try:
            schedule = MaintenanceSchedule.objects.get(id=schedule_id)
            form = MaintenanceScheduleForm(instance=schedule)
            context = {
                'form': form,
                'schedule': schedule,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': f'Edit Maintenance - {schedule.maintenance_type}'
            }
            return render(request, self.get_template_name(), context)
        except MaintenanceSchedule.DoesNotExist:
            messages.error(request, "Maintenance schedule not found")
            return redirect('maintenance_schedule')
        except Exception as e:
            logger.error(f"Error in edit maintenance view: {str(e)}")
            messages.error(request, "An error occurred while loading the maintenance schedule")
            return handler500(request, exception=str(e))

    def post(self, request, schedule_id):
        try:
            schedule = MaintenanceSchedule.objects.get(id=schedule_id)
            form = MaintenanceScheduleForm(request.POST, instance=schedule)
            if form.is_valid():
                updated_schedule = form.save()
                messages.success(request, "Maintenance schedule updated successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Maintenance schedule updated successfully',
                    'redirect_url': reverse('maintenance_schedule')
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
            
        except MaintenanceSchedule.DoesNotExist:
            messages.error(request, "Maintenance schedule not found")
            return JsonResponse({
                'status': 'error',
                'message': 'Maintenance schedule not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating maintenance schedule: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to update maintenance schedule'
            }, status=500)

class DeleteMaintenanceScheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_delete(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.test_func():
                logger.warning(f"Access denied to maintenance deletion for user {request.user.id}")
                messages.error(request, "You don't have permission to delete maintenance schedules")
                return handler403(request, exception="Access Denied")
                
            if request.method != 'POST':
                return handler403(request, exception="Method not allowed")
                
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in maintenance delete dispatch: {str(e)}")
            messages.error(request, "An error occurred while processing your request")
            return redirect('maintenance_schedule')

    def post(self, request, schedule_id):
        try:
            schedule = get_object_or_404(MaintenanceSchedule, pk=schedule_id)
            maintenance_type = schedule.maintenance_type
            asset_name = schedule.asset.name
            schedule.delete()
            messages.success(request, f"Maintenance schedule '{maintenance_type}' for '{asset_name}' deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting maintenance schedule {schedule_id}: {str(e)}")
            messages.error(request, "Error deleting maintenance schedule")
        
        return redirect('maintenance_schedule')