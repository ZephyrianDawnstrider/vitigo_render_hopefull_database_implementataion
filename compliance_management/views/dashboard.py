# Standard Library imports
import json
import logging
from datetime import timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Avg
from django.shortcuts import render
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

# Local/Relative imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import (
    ComplianceAlert,
    ComplianceIssue,
    ComplianceMetric,
    ComplianceReminder,
    ComplianceSchedule,
    ComplianceNote,
    ComplianceReport,
    PatientGroup
)
from ..utils import get_template_path

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceManagementDashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        try:
            return [get_template_path(
                'dashboard/dashboard.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading dashboard template"
            )

    def get_context_data(self, **kwargs):
        if not self.request.user.is_authenticated:
            return handler401(self.request, exception="Authentication required")

        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        try:
            # Key Metrics
            context.update(self.get_key_metrics(today))
            context.update(self.get_compliance_metrics(today))
            context.update(self.get_issues_and_schedules(today))
            context.update(self.get_alerts_and_trends(today))
            
            # Add recent notes count with error handling
            try:
                recent_notes_count = ComplianceNote.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count()
                context['recent_notes_count'] = recent_notes_count
            except Exception as note_error:
                logger.error(f"Error getting recent notes count: {str(note_error)}")
                context['recent_notes_count'] = 0

            return context

        except Exception as e:
            logger.error(f"Dashboard data error: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading dashboard data")
            # Instead of returning handler500, provide default context
            self.provide_default_context(context)
            context['error_message'] = "Error loading dashboard data"
            return context

    def get_key_metrics(self, today):
        try:
            return {
                'active_schedules_count': ComplianceSchedule.objects.filter(
                    scheduled_date=today,
                    status__in=['SCHEDULED', 'IN_PROGRESS']
                ).count(),
                'open_issues_count': ComplianceIssue.objects.filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).count(),
                'pending_reminders': ComplianceReminder.objects.filter(
                    status='PENDING',
                    scheduled_datetime__date=today
                ).count(),
                'active_alerts': ComplianceAlert.objects.filter(
                    is_resolved=False
                ).count(),
                'recent_reports_count': ComplianceReport.objects.filter(
                    generated_at__gte=timezone.now() - timedelta(days=30)
                ).count(),
                'patient_groups_count': PatientGroup.objects.filter(
                    is_active=True
                ).count(),
            }
        except Exception as e:
            logger.error(f"Key metrics error: {str(e)}")
            raise

    def get_compliance_metrics(self, today):
        try:
            metrics = ComplianceMetric.objects.filter(
                evaluation_date=today
            ).aggregate(
                avg_medication=Avg('compliance_score', filter=Q(metric_type='MEDICATION')),
                avg_appointment=Avg('compliance_score', filter=Q(metric_type='APPOINTMENT')),
                avg_overall=Avg('compliance_score', filter=Q(metric_type='OVERALL'))
            )
            
            return {
                'compliance_metrics': {
                    'medication': round(metrics['avg_medication'] or 0, 1),
                    'appointment': round(metrics['avg_appointment'] or 0, 1),
                    'overall': round(metrics['avg_overall'] or 0, 1)
                }
            }
        except Exception as e:
            logger.error(f"Compliance metrics error: {str(e)}")
            raise

    def get_issues_and_schedules(self, today):
        try:
            return {
                'recent_issues': ComplianceIssue.objects.select_related(
                    'patient', 'assigned_to'
                ).filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).order_by('-created_at')[:5],
                
                'schedule_summary': ComplianceSchedule.objects.filter(
                    scheduled_date=today
                ).values('status').annotate(
                    count=Count('id')
                ).order_by('status')
            }
        except Exception as e:
            logger.error(f"Issues and schedules error: {str(e)}")
            raise

    def get_alerts_and_trends(self, today):
        try:
            weekly_metrics = []
            for i in range(7):
                date = today - timedelta(days=i)
                daily_metrics = ComplianceMetric.objects.filter(
                    evaluation_date=date
                ).aggregate(
                    avg_score=Avg('compliance_score')
                )
                weekly_metrics.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'score': round(daily_metrics['avg_score'] or 0, 1)
                })
            
            return {
                'alerts_distribution': ComplianceAlert.objects.filter(
                    is_resolved=False
                ).values('alert_type', 'severity').annotate(
                    count=Count('id')
                ).order_by('-count'),
                'weekly_metrics': json.dumps(weekly_metrics, cls=DjangoJSONEncoder)
            }
        except Exception as e:
            logger.error(f"Alerts and trends error: {str(e)}")
            raise

    def provide_default_context(self, context):
        """Provide default values for context in case of errors"""
        context.update({
            'active_schedules_count': 0,
            'open_issues_count': 0,
            'pending_reminders': 0,
            'active_alerts': 0,
            'compliance_metrics': {'medication': 0, 'appointment': 0, 'overall': 0},
            'recent_issues': [],
            'schedule_summary': [],
            'alerts_distribution': [],
            'weekly_metrics': '[]',
            'recent_reports_count': 0,
            'patient_groups_count': 0,
        })

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, exception="Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(f"Access denied for user {request.user} to compliance management")
                return handler403(request, exception="Access denied to compliance management")

            # Add session tracking for audit purposes
            request.session['last_compliance_action'] = 'dashboard_access'
            request.session['compliance_access_time'] = timezone.now().isoformat()

            return super().dispatch(request, *args, **kwargs)
            
        except PermissionError as e:
            logger.error(f"Permission error: {str(e)}")
            return handler403(request, exception=str(e))
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, exception="Error accessing compliance management")

    def handle_no_permission(self):
        return handler403(
            self.request, 
            exception="You don't have permission to access this page"
        )