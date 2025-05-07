# Standard library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.db import models
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from hr_management.models import Department, Employee, Position
from hr_management.forms import DepartmentForm
from hr_management.utils import get_template_path

# Initialize logger
logger = logging.getLogger(__name__)

class DepartmentListView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('departments/department_list.html', self.request.user.role, 'hr_management')

    def get(self, request):
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')

        departments = Department.objects.annotate(
            employee_count=Count('employees', filter=Q(employees__is_active=True))
        )

        # Apply filters
        if search_query:
            departments = departments.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query)
            )

        if status_filter:
            departments = departments.filter(is_active=(status_filter == 'active'))

        # Pagination
        paginator = Paginator(departments, 10)
        page = request.GET.get('page', 1)
        try:
            departments_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            departments_page = paginator.page(1)

        context = {
            'departments': departments_page,
            'search_query': search_query,
            'status_filter': status_filter,
        }

        return render(request, self.get_template_name(), context)

class NewDepartmentView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('departments/new_department.html', self.request.user.role, 'hr_management')

    def get(self, request):
        form = DepartmentForm()
        return render(request, self.get_template_name(), {'form': form})

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            try:
                department = form.save()
                messages.success(request, "Department created successfully")
                return redirect('department_list')
            except Exception as e:
                logger.error(f"Error creating department: {str(e)}")
                messages.error(request, "Error creating department")
                return render(request, self.get_template_name(), {'form': form})
        
        return render(request, self.get_template_name(), {'form': form})

class DepartmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Department
    context_object_name = 'department'

    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.test_func():
                logger.warning(f"Access denied to department details for user {request.user.id}")
                messages.error(request, "You don't have permission to view department details")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in department detail dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the department details")
            return redirect('dashboard')

    def get_template_names(self):
        try:
            return [get_template_path(
                'departments/department_detail.html',
                self.request.user.role,
                'hr_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['hr_management/default_department_detail.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = self.object
        
        try:
            # Get employees in this department
            employees = Employee.objects.filter(department=department)
            context['employees'] = employees
            context['employee_count'] = employees.count()
            
            # Get positions in this department
            positions = Position.objects.filter(department=department)
            context['positions'] = positions
            context['position_count'] = positions.count()
            
            # Get subdepartments
            subdepartments = Department.objects.filter(parent=department)
            context['subdepartments'] = subdepartments
            context['subdepartment_count'] = subdepartments.count()
            
        except Exception as e:
            logger.error(f"Error fetching department details for {department.id}: {str(e)}")
            messages.error(self.request, "Some department data could not be loaded")
        
        return context

class DepartmentEditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('departments/edit_department.html', self.request.user.role, 'hr_management')

    def get(self, request, pk):
        try:
            department = get_object_or_404(Department, pk=pk)
            form = DepartmentForm(instance=department)
            return render(request, self.get_template_name(), {
                'form': form,
                'department': department
            })
        except Exception as e:
            logger.error(f"Error retrieving department for edit: {str(e)}")
            messages.error(request, "Error retrieving department details")
            return redirect('department_list')

    def post(self, request, pk):
        try:
            department = get_object_or_404(Department, pk=pk)
            form = DepartmentForm(request.POST, instance=department)
            
            if form.is_valid():
                form.save()
                messages.success(request, "Department updated successfully")
                return redirect('department_detail', pk=pk)
            
            return render(request, self.get_template_name(), {
                'form': form,
                'department': department
            })
        except Exception as e:
            logger.error(f"Error updating department: {str(e)}")
            messages.error(request, "Error updating department")
            return render(request, self.get_template_name(), {
                'form': form,
                'department': department
            })

class DepartmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_delete(self.request.user, 'hr_management')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.test_func():
                logger.warning(f"Access denied to department deletion for user {request.user.id}")
                messages.error(request, "You don't have permission to delete departments")
                return handler403(request, exception="Access Denied")
                
            if request.method != 'POST':
                return handler403(request, exception="Method not allowed")
                
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in department delete dispatch: {str(e)}")
            messages.error(request, "An error occurred while processing your request")
            return redirect('department_list')

    def post(self, request, pk):
        try:
            department = get_object_or_404(Department, pk=pk)
            department_name = department.name
            
            # Check if department has employees
            if department.employees.exists():
                messages.error(request, "Cannot delete department with active employees")
                return redirect('department_detail', pk=pk)
                
            # Check if department has subdepartments
            if Department.objects.filter(parent=department).exists():
                messages.error(request, "Cannot delete department with subdepartments")
                return redirect('department_detail', pk=pk)
                
            department.delete()
            messages.success(request, f"Department '{department_name}' deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting department {pk}: {str(e)}")
            messages.error(request, "Error deleting department")
        
        return redirect('department_list')