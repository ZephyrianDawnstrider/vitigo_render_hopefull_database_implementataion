# Standard library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db import models
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from django.core.exceptions import ValidationError
from django.views.generic import DetailView

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from hr_management.models import Leave, LeaveSettings
from hr_management.utils import get_template_path

from datetime import datetime, timedelta
from calendar import monthrange

logger = logging.getLogger(__name__)

class LeaveListView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('leaves/leave_list.html', self.request.user.role, 'hr_management')

    def get(self, request):
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')

        leaves = Leave.objects.select_related(
            'employee__user', 
            'employee__department'
        ).all().order_by('-created_at')

        # Apply filters
        if search_query:
            leaves = leaves.filter(
                Q(employee__user__first_name__icontains=search_query) |
                Q(employee__user__last_name__icontains=search_query) |
                Q(employee__employee_id__icontains=search_query)
            )

        if status_filter:
            leaves = leaves.filter(status=status_filter)

        if type_filter:
            leaves = leaves.filter(leave_type=type_filter)

        # Pagination
        paginator = Paginator(leaves, 10)
        page = request.GET.get('page', 1)
        try:
            leaves_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            leaves_page = paginator.page(1)

        context = {
            'leaves': leaves_page,
            'search_query': search_query,
            'status_filter': status_filter,
            'type_filter': type_filter
        }

        return render(request, self.get_template_name(), context)

class PendingLeaveRequestsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('leaves/pending_requests.html', self.request.user.role, 'hr_management')

    def get(self, request):
        pending_leaves = Leave.objects.select_related(
            'employee__user', 
            'employee__department'
        ).filter(status='PENDING').order_by('-created_at')

        # Get pending count for badge
        pending_count = pending_leaves.count()

        context = {
            'pending_leaves': pending_leaves,
            'pending_count': pending_count
        }

        return render(request, self.get_template_name(), context)

class LeaveCalendarView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('leaves/leave_calendar.html', self.request.user.role, 'hr_management')

    def get(self, request):
        # Get current year and month
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        
        # Get first and last day of month
        _, last_day = monthrange(year, month)
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, last_day).date()
        
        # Get all leaves for the month
        leaves = Leave.objects.select_related(
            'employee__user'
        ).filter(
            (Q(start_date__range=[start_date, end_date]) | 
             Q(end_date__range=[start_date, end_date])) &
            Q(status__in=['APPROVED', 'PENDING'])
        )

        # Organize leaves by date
        calendar_data = {}
        current_date = start_date
        while current_date <= end_date:
            calendar_data[current_date] = []
            for leave in leaves:
                if leave.start_date <= current_date <= leave.end_date:
                    calendar_data[current_date].append(leave)
            current_date += timedelta(days=1)

        context = {
            'calendar_data': calendar_data,
            'year': year,
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%B'),
            'prev_month': (datetime(year, month, 1) - timedelta(days=1)).strftime('%Y-%m'),
            'next_month': (datetime(year, month, last_day) + timedelta(days=1)).strftime('%Y-%m'),
        }

        return render(request, self.get_template_name(), context)

class LeaveSettingsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('leaves/leave_settings.html', self.request.user.role, 'hr_management')

    def get(self, request):
        settings = LeaveSettings.objects.all()
        context = {
            'settings': settings,
            'leave_types': Leave.LEAVE_TYPE_CHOICES
        }
        return render(request, self.get_template_name(), context)

    def post(self, request):
        leave_type = request.POST.get('leave_type')
        try:
            setting = LeaveSettings.objects.get(leave_type=leave_type)
        except LeaveSettings.DoesNotExist:
            setting = LeaveSettings(leave_type=leave_type)

        setting.annual_allowance = request.POST.get('annual_allowance', 0)
        setting.carry_forward_limit = request.POST.get('carry_forward_limit', 0)
        setting.min_service_days = request.POST.get('min_service_days', 0)
        setting.requires_approval = request.POST.get('requires_approval') == 'on'
        setting.requires_documentation = request.POST.get('requires_documentation') == 'on'
        setting.documentation_info = request.POST.get('documentation_info', '')
        setting.notice_period_days = request.POST.get('notice_period_days', 0)
        setting.is_active = request.POST.get('is_active') == 'on'

        try:
            setting.full_clean()
            setting.save()
            messages.success(request, f'Settings for {setting.get_leave_type_display()} updated successfully')
        except ValidationError as e:
            messages.error(request, f'Error updating settings: {e}')

        return redirect('leave_settings')

class LeaveDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Leave
    context_object_name = 'leave'

    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.test_func():
                logger.warning(f"Access denied to leave details for user {request.user.id}")
                messages.error(request, "You don't have permission to view leave details")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in leave detail dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the leave details")
            return redirect('leave_list')

    def get_template_names(self):
        try:
            return [get_template_path(
                'leaves/leave_detail.html',
                self.request.user.role,
                'hr_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['hr_management/default_leave_detail.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leave = self.object
        
        try:
            # Add any additional context data needed for the template
            context['employee'] = leave.employee
            context['department'] = leave.employee.department
            context['leave_duration'] = (leave.end_date - leave.start_date).days + 1
            
            # Get leave history for this employee
            context['leave_history'] = Leave.objects.filter(
                employee=leave.employee
            ).exclude(
                id=leave.id
            ).order_by('-start_date')[:5]
            
        except Exception as e:
            logger.error(f"Error fetching leave details for {leave.id}: {str(e)}")
            messages.error(self.request, "Some leave data could not be loaded")
        
        return context

class LeaveActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.test_func():
                logger.warning(f"Access denied to leave actions for user {request.user.id}")
                messages.error(request, "You don't have permission to process leave requests")
                return handler403(request, exception="Access Denied")
                
            if request.method != 'POST':
                return handler403(request, exception="Method not allowed")
                
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in leave action dispatch: {str(e)}")
            messages.error(request, "An error occurred while processing your request")
            return redirect('leave_list')

    def post(self, request, pk, action):
        try:
            leave = Leave.objects.get(pk=pk)
            
            if leave.status != 'PENDING':
                messages.error(request, "This leave request has already been processed")
                return redirect('leave_detail', pk=pk)
            
            if action == 'approve':
                leave.status = 'APPROVED'
                message = "Leave request approved successfully"
            elif action == 'reject':
                leave.status = 'REJECTED'
                message = "Leave request rejected successfully"
            else:
                messages.error(request, "Invalid action")
                return redirect('leave_detail', pk=pk)
            
            leave.approved_by = request.user
            leave.approved_at = timezone.now()
            leave.save()
            
            messages.success(request, message)
            
        except Leave.DoesNotExist:
            logger.error(f"Leave request {pk} not found")
            messages.error(request, "Leave request not found")
        except Exception as e:
            logger.error(f"Error processing leave action: {str(e)}")
            messages.error(request, "Error processing leave request")
        
        return redirect('leave_detail', pk=pk)