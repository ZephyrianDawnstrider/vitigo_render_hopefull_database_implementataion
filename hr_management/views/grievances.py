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

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from hr_management.models import Grievance
from hr_management.forms import GrievanceEditForm
from hr_management.utils import get_template_path

# Initialize logger
logger = logging.getLogger(__name__)

class GrievanceListView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('grievances/grievance_list.html', self.request.user.role, 'hr_management')

    def get(self, request):
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        priority_filter = request.GET.get('priority', '')

        grievances = Grievance.objects.select_related(
            'employee__user',
            'employee__department'
        ).all().order_by('-filed_date')

        # Apply filters
        if search_query:
            grievances = grievances.filter(
                Q(employee__user__first_name__icontains=search_query) |
                Q(employee__user__last_name__icontains=search_query) |
                Q(subject__icontains=search_query)
            )

        if status_filter:
            grievances = grievances.filter(status=status_filter)

        if priority_filter:
            grievances = grievances.filter(priority=priority_filter)

        # Pagination
        paginator = Paginator(grievances, 10)
        page = request.GET.get('page', 1)
        try:
            grievances_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            grievances_page = paginator.page(1)

        context = {
            'grievances': grievances_page,
            'search_query': search_query,
            'status_filter': status_filter,
            'priority_filter': priority_filter,
            'status_choices': dict(Grievance.STATUS_CHOICES),
            'priority_choices': dict(Grievance.PRIORITY_CHOICES)
        }

        return render(request, self.get_template_name(), context)

class GrievanceDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('grievances/grievance_detail.html', self.request.user.role, 'hr_management')

    def get(self, request, pk):
        try:
            grievance = Grievance.objects.select_related(
                'employee__user',
                'employee__department',
                'assigned_to'
            ).get(pk=pk)
            
            context = {
                'grievance': grievance,
                'status_choices': dict(Grievance.STATUS_CHOICES),
                'priority_choices': dict(Grievance.PRIORITY_CHOICES)
            }
            
            return render(request, self.get_template_name(), context)
            
        except Grievance.DoesNotExist:
            messages.error(request, "Grievance not found")
            return redirect('grievance_list')

class GrievanceEditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('grievances/grievance_edit.html', self.request.user.role, 'hr_management')

    def get(self, request, pk):
        try:
            grievance = Grievance.objects.select_related(
                'employee__user',
                'employee__department'
            ).get(pk=pk)
            
            if grievance.status == 'CLOSED':
                messages.error(request, "Cannot edit closed grievances")
                return redirect('grievance_detail', pk=pk)
                
            form = GrievanceEditForm(instance=grievance)
            context = {
                'form': form,
                'grievance': grievance
            }
            return render(request, self.get_template_name(), context)
            
        except Grievance.DoesNotExist:
            messages.error(request, "Grievance not found")
            return redirect('grievance_list')

    def post(self, request, pk):
        try:
            grievance = Grievance.objects.get(pk=pk)
            
            if grievance.status == 'CLOSED':
                messages.error(request, "Cannot edit closed grievances")
                return redirect('grievance_detail', pk=pk)
                
            form = GrievanceEditForm(request.POST, instance=grievance)
            if form.is_valid():
                grievance = form.save(commit=False)
                if grievance.status in ['RESOLVED', 'CLOSED']:
                    grievance.resolved_date = timezone.now()
                grievance.save()
                
                messages.success(request, "Grievance updated successfully")
                return redirect('grievance_detail', pk=pk)
            
            context = {
                'form': form,
                'grievance': grievance
            }
            return render(request, self.get_template_name(), context)
            
        except Grievance.DoesNotExist:
            messages.error(request, "Grievance not found")
            return redirect('grievance_list')