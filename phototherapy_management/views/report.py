# Standard library imports
import logging
from datetime import timedelta, datetime

# Django imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Avg, Sum, F, DurationField
from django.db.models.expressions import ExpressionWrapper
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import View

from phototherapy_management.models import (
    ProblemReport,
    PhototherapySession,
    DeviceMaintenance,
    PhototherapyProgress
)
from phototherapy_management.utils import get_template_path
from error_handling.views import handler500

# Configure logging
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()


class ReportManagementView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get filter parameters
            search_query = request.GET.get('search', '')
            status = request.GET.get('status', '')
            sort_by = request.GET.get('sort', '-reported_at')
            date_range = request.GET.get('date_range', '30')

            # Base querysets
            today = timezone.now().date()
            start_date = today - timedelta(days=int(date_range))
            
            # Problem Reports Analysis with filters
            problem_reports = ProblemReport.objects.select_related(
                'session', 'reported_by', 'resolved_by'
            )

            # Apply filters
            if search_query:
                problem_reports = problem_reports.filter(
                    Q(problem_description__icontains=search_query) |
                    Q(session__plan__patient__first_name__icontains=search_query) |
                    Q(session__plan__patient__last_name__icontains=search_query)
                )
            
            if status:
                problem_reports = problem_reports.filter(
                    resolved=(status == 'resolved')
                )

            # Apply sorting
            if sort_by:
                problem_reports = problem_reports.order_by(sort_by)

            # Filter by date range
            problem_reports = problem_reports.filter(reported_at__date__gte=start_date)

            problem_reports = problem_reports.annotate(
                resolution_time=ExpressionWrapper(
                    F('resolved_at') - F('reported_at'),
                    output_field=DurationField()
                )
            )
            
            problem_stats = {
                'total': problem_reports.count(),
                'unresolved': problem_reports.filter(resolved=False).count(),
                'critical': problem_reports.filter(severity='SEVERE').count(),
                'avg_resolution_time': problem_reports.filter(
                    resolved=True
                ).aggregate(avg_time=Avg('resolution_time'))['avg_time']
            }

            # Progress Tracking
            progress_records = PhototherapyProgress.objects.select_related(
                'plan', 'assessed_by'
            ).filter(
                assessment_date__gte=start_date
            )
            
            progress_stats = {
                'total_assessments': progress_records.count(),
                'avg_improvement': progress_records.aggregate(
                    avg=Avg('improvement_percentage')
                )['avg'],
                'excellent_response': progress_records.filter(
                    response_level='EXCELLENT'
                ).count(),
                'poor_response': progress_records.filter(
                    response_level__in=['POOR', 'NO_RESPONSE']
                ).count()
            }

            # Device Maintenance Reports
            maintenance_records = DeviceMaintenance.objects.select_related(
                'device', 'created_by'
            )
            
            maintenance_stats = {
                'total_maintenance': maintenance_records.count(),
                'pending_maintenance': maintenance_records.filter(
                    next_maintenance_due__lte=today
                ).count(),
                'total_cost': maintenance_records.filter(
                    maintenance_date__gte=start_date
                ).aggregate(total=Sum('cost'))['total'] or 0
            }

            # Compliance Tracking
            sessions = PhototherapySession.objects.filter(
                scheduled_date__gte=start_date
            )
            
            compliance_stats = {
                'total_sessions': sessions.count(),
                'completed': sessions.filter(status='COMPLETED').count(),
                'missed': sessions.filter(status='MISSED').count(),
                'compliance_rate': (sessions.filter(status='COMPLETED').count() / 
                                  sessions.count() * 100) if sessions.count() > 0 else 0
            }

            context = {
                'problem_stats': problem_stats,
                'progress_stats': progress_stats,
                'maintenance_stats': maintenance_stats,
                'compliance_stats': compliance_stats,
                'recent_problems': problem_reports[:10],
                'pending_maintenance': maintenance_records.filter(
                    next_maintenance_due__lte=today
                ).order_by('next_maintenance_due')[:5],
                'recent_progress': progress_records.order_by(
                    '-assessment_date'
                )[:5],
                'search_query': search_query,
                'current_status': status,
                'current_sort': sort_by,
                'current_date_range': date_range
            }

            template_path = get_template_path(
                'report_management.html',
                request.user.role,
                'phototherapy_management'
            )
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in report management view: {str(e)}")
            messages.error(request, "An error occurred while loading report data")
            return handler500(request, exception=str(e))