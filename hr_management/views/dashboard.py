# Standard library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.db import models
from django.shortcuts import render
from django.utils import timezone
from django.views import View

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from hr_management.models import Notice, TrainingParticipant
from hr_management.utils import get_template_path

# Initialize logger
logger = logging.getLogger(__name__)

class HRManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to access HR Management")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        # Use 'dashboard/dashboard.html' for Administrator role since template exists there
        role = self.request.user.role
        if role and role.name.lower() == 'administrator':
            return get_template_path('dashboard/dashboard.html', role, 'hr_management')
        else:
            return get_template_path('dashboard.html', role, 'hr_management')

    def get_dashboard_stats(self):
        """Get key statistics for HR dashboard"""
        try:
            from hr_management.models import Employee, Department, Leave, Training, Grievance
            current_date = timezone.now().date()

            stats = {
                'total_employees': Employee.objects.filter(is_active=True).count(),
                'departments': Department.objects.filter(is_active=True).count(),
                'pending_leaves': Leave.objects.filter(status='PENDING').count(),
                'active_trainings': Training.objects.filter(
                    Q(status='IN_PROGRESS') 
                ).count(),
                'open_grievances': Grievance.objects.filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).count(),
            }
            
            # Add debug logging
            logger.debug(f"Active trainings query result: {stats['active_trainings']}")
            logger.debug(f"Current date for comparison: {current_date}")
            
            # Log details of all IN_PROGRESS trainings
            in_progress_trainings = Training.objects.filter(status='IN_PROGRESS')
            logger.debug(f"All IN_PROGRESS trainings: {list(in_progress_trainings.values('id', 'title', 'start_date', 'end_date', 'status'))}")
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return {}

    def get_department_stats(self):
        """Get department-wise employee distribution"""
        try:
            from hr_management.models import Department
            dept_stats = Department.objects.annotate(
                employee_count=Count('employees', filter=Q(employees__is_active=True))
            ).filter(is_active=True).values('name', 'employee_count')
            return list(dept_stats)
        except Exception as e:
            logger.error(f"Error getting department stats: {str(e)}")
            return []

    def get_recent_activities(self):
        """Get recent HR activities"""
        try:
            from hr_management.models import Employee, Leave, Training, Grievance
            
            # Get last 5 activities of each type
            recent_employees = Employee.objects.filter(
                is_active=True
            ).order_by('-created_at')[:5]
            
            recent_leaves = Leave.objects.filter(
                start_date__gte=timezone.now().date()
            ).order_by('start_date')[:5]
            
            recent_trainings = Training.objects.filter(
                status__in=['PLANNED', 'IN_PROGRESS']
            ).order_by('-created_at')[:5]
            
            recent_grievances = Grievance.objects.exclude(
                status='CLOSED'
            ).order_by('-filed_date')[:5]

            return {
                'recent_employees': recent_employees,
                'recent_leaves': recent_leaves,
                'recent_trainings': recent_trainings,
                'recent_grievances': recent_grievances
            }
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
            return {}

    def get_leave_stats(self):
        """Get leave statistics"""
        try:
            from hr_management.models import Leave
            current_month = timezone.now().month
            
            leave_stats = Leave.objects.filter(
                start_date__month=current_month
            ).aggregate(
                approved=Count('id', filter=Q(status='APPROVED')),
                pending=Count('id', filter=Q(status='PENDING')),
                rejected=Count('id', filter=Q(status='REJECTED'))
            )
            return leave_stats
        except Exception as e:
            logger.error(f"Error getting leave stats: {str(e)}")
            return {}

    def get_upcoming_reviews(self):
        """Get upcoming performance reviews in the next 30 days"""
        try:
            from hr_management.models import PerformanceReview
            current_date = timezone.now().date()
            thirty_days_later = current_date + timezone.timedelta(days=30)
            
            return PerformanceReview.objects.filter(
                review_date__range=[current_date, thirty_days_later],
                status='DRAFT'
            ).select_related('employee').order_by('review_date')[:5]
        except Exception as e:
            logger.error(f"Error getting upcoming reviews: {str(e)}")
            return []

    def get_expiring_documents(self):
        """Get documents expiring in the next 30 days"""
        try:
            from hr_management.models import Document
            current_date = timezone.now().date()
            thirty_days_later = current_date + timezone.timedelta(days=30)
            
            documents = Document.objects.filter(
                expiry_date__range=[current_date, thirty_days_later]
            ).select_related('employee').order_by('expiry_date')
            
            # Add days_until_expiry to each document
            for doc in documents:
                doc.days_until_expiry = (doc.expiry_date - current_date).days
            
            return documents[:5]
        except Exception as e:
            logger.error(f"Error getting expiring documents: {str(e)}")
            return []

    def get_key_metrics(self):
        """Calculate key performance metrics"""
        try:
            from hr_management.models import Training, Employee, PerformanceReview
            from django.db.models import Avg
            current_date = timezone.now().date()
            thirty_days_ago = current_date - timezone.timedelta(days=30)

            # Training completion rate
            total_trainings = TrainingParticipant.objects.filter(
                training__end_date__lte=current_date
            ).count()
            completed_trainings = TrainingParticipant.objects.filter(
                training__end_date__lte=current_date,
                status='COMPLETED'
            ).count()
            training_completion_rate = (completed_trainings / total_trainings * 100) if total_trainings > 0 else 0

            # Average time to hire (last 30 days)
            recent_hires = Employee.objects.filter(
                join_date__gte=thirty_days_ago
            ).aggregate(
                avg_days=Avg(models.F('join_date') - models.F('created_at'))
            )
            avg_time_to_hire = recent_hires['avg_days'].days if recent_hires['avg_days'] else 0

            # Employee satisfaction (from performance reviews)
            recent_satisfaction = PerformanceReview.objects.filter(
                review_date__gte=thirty_days_ago
            ).aggregate(
                avg_satisfaction=Avg(
                    (models.F('technical_skills') + 
                     models.F('communication') + 
                     models.F('teamwork') + 
                     models.F('productivity') + 
                     models.F('reliability')) / 5.0
                )
            )
            employee_satisfaction = round(recent_satisfaction['avg_satisfaction'] or 0, 1)

            # Retention rate calculation
            total_employees_start = Employee.objects.filter(
                join_date__lte=thirty_days_ago,
                is_active=True
            ).count()
            employees_left = Employee.objects.filter(
                end_date__range=[thirty_days_ago, current_date]
            ).count()
            retention_rate = ((total_employees_start - employees_left) / total_employees_start * 100) if total_employees_start > 0 else 100

            return {
                'training_completion_rate': training_completion_rate,
                'avg_time_to_hire': avg_time_to_hire,
                'employee_satisfaction': employee_satisfaction,
                'retention_rate': retention_rate,
                # Include month-over-month changes
                'training_rate_change': 12.0,  # Example: +12% improvement
                'time_to_hire_change': 3,      # Example: +3 days (negative change)
                'satisfaction_change': 5.0,     # Example: +5% improvement
                'retention_rate_change': 2.0    # Example: +2% improvement
            }
        except Exception as e:
            logger.error(f"Error calculating key metrics: {str(e)}")
            return {}

    def get_important_notices(self):
        """Get active important notices"""
        try:
            current_date = timezone.now().date()
            return Notice.objects.filter(
                is_active=True,
                expiry_date__gte=current_date
            ).order_by('-priority', '-created_at')[:3]
        except Exception as e:
            logger.error(f"Error getting important notices: {str(e)}")
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['important_notices'] = Notice.objects.filter(
            is_active=True,
            expiry_date__gte=timezone.now().date()
        ).order_by('-priority', '-created_at')[:5]
        return context

    def get(self, request):
        try:
            template_path = self.get_template_name()
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            # Prepare context with all dashboard data
            context = {
                'dashboard_stats': self.get_dashboard_stats(),
                'department_stats': self.get_department_stats(),
                'recent_activities': self.get_recent_activities(),
                'leave_stats': self.get_leave_stats(),
                'upcoming_reviews': self.get_upcoming_reviews(),
                'expiring_documents': self.get_expiring_documents(),
                'key_metrics': self.get_key_metrics(),
                'important_notices': self.get_important_notices(),
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'HR Management',
                'page_title': 'HR Dashboard',
            }

            return render(request, template_path, context)
            
        except Exception as e:
            logger.exception(f"Error in HRManagementView: {str(e)}")
            messages.error(request, "An error occurred while loading the HR dashboard.")
            return handler500(request, exception=str(e))