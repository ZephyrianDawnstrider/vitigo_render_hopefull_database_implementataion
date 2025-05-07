# Standard Library imports
import json
import logging
from datetime import timedelta

# Django imports
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.views.generic import TemplateView

# Local imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import (
    Procedure, ProcedureType, ProcedureCategory,
    ConsentForm, ProcedureChecklist, ProcedureMedia
)
from ..utils import get_template_path

logger = logging.getLogger(__name__)

class ProcedureManagementView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        try:
            return [get_template_path(
                'dashboard/dashboard.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading dashboard template")

    def get_context_data(self, **kwargs):
        if not self.request.user.is_authenticated:
            return handler401(self.request, "Authentication required")

        context = super().get_context_data(**kwargs)
        
        try:
            today = timezone.now().date()
            additional_context = {
                # Key metrics
                'total_procedures': Procedure.objects.count(),
                'today_procedures': Procedure.objects.filter(scheduled_date=today).count(),
                'pending_consents': ConsentForm.objects.filter(signed_by_patient=False).count(),
                
                # Procedure statistics
                'procedure_by_status': Procedure.objects.values('status').annotate(
                    count=Count('id')
                ).order_by('status'),
                
                # Recent procedures
                'recent_procedures': Procedure.objects.select_related(
                    'procedure_type', 'patient', 'primary_doctor'
                ).order_by('-scheduled_date')[:5],
                
                # Categories and types
                'procedure_categories': ProcedureCategory.objects.annotate(
                    type_count=Count('procedure_types')
                ).order_by('-type_count')[:5],
                
                # Checklists and media
                'incomplete_checklists': ProcedureChecklist.objects.filter(
                    completed_items__is_completed=False
                ).distinct().count(),
                
                'recent_media': ProcedureMedia.objects.select_related(
                    'procedure'
                ).order_by('-uploaded_at')[:5],
                
                # Procedure trends
                'weekly_trends': self.get_weekly_trends(),
                
                # Priority distribution
                'priority_distribution': ProcedureType.objects.values(
                    'priority'
                ).annotate(count=Count('id')),
                
                # Add status distribution data
                'status_distribution': json.dumps(self.get_status_distribution()),
            }
            context.update(additional_context)
            return context

        except Exception as e:
            logger.error(f"Dashboard data error: {str(e)}", exc_info=True)
            default_context = self.get_default_context()
            context.update(default_context)
            return context

    def get_weekly_trends(self):
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=6)
            
            daily_counts = []
            date_labels = []
            
            for i in range(7):
                current_date = end_date - timedelta(days=i)
                count = Procedure.objects.filter(scheduled_date=current_date).count()
                daily_counts.insert(0, count)
                date_labels.insert(0, current_date.strftime('%b %d'))

            return json.dumps({
                'labels': date_labels,
                'datasets': [{
                    'label': 'Daily Procedures',
                    'data': daily_counts,
                    'borderColor': '#4f46e5',
                    'backgroundColor': 'rgba(79, 70, 229, 0.1)',
                    'tension': 0.4,
                    'fill': True
                }]
            }, cls=DjangoJSONEncoder)
        except Exception as e:
            logger.error(f"Error generating weekly trends: {str(e)}")
            return json.dumps({
                'labels': [],
                'datasets': [{
                    'label': 'Daily Procedures',
                    'data': [],
                    'borderColor': '#4f46e5',
                    'backgroundColor': 'rgba(79, 70, 229, 0.1)',
                    'tension': 0.4,
                    'fill': True
                }]
            })

    def get_status_distribution(self):
        status_data = Procedure.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Define colors for each status
        status_colors = {
            'SCHEDULED': '#3b82f6',    # blue-500
            'CONSENT_PENDING': '#f59e0b', # amber-500
            'READY': '#10b981',        # emerald-500
            'IN_PROGRESS': '#6366f1',  # indigo-500
            'COMPLETED': '#22c55e',    # green-500
            'CANCELLED': '#ef4444',    # red-500
        }
        
        return {
            'labels': [item['status'].replace('_', ' ').title() for item in status_data],
            'datasets': [{
                'data': [item['count'] for item in status_data],
                'backgroundColor': [status_colors.get(item['status'], '#6b7280') for item in status_data],
            }]
        }

    def get_default_context(self):
        """Provide default values for context in case of errors"""
        return {
            'total_procedures': 0,
            'today_procedures': 0,
            'pending_consents': 0,
            'procedure_by_status': [],
            'recent_procedures': [],
            'procedure_categories': [],
            'incomplete_checklists': 0,
            'recent_media': [],
            'weekly_trends': json.dumps({
                'labels': [],
                'datasets': [{
                    'label': 'Daily Procedures',
                    'data': [],
                    'borderColor': '#4f46e5',
                    'backgroundColor': 'rgba(79, 70, 229, 0.1)',
                    'tension': 0.4,
                    'fill': True
                }]
            }),
            'priority_distribution': [],
            'error_message': "Error loading dashboard data",
            'status_distribution': json.dumps({
                'labels': [],
                'datasets': [{'data': [], 'backgroundColor': []}]
            }),
        }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to procedure management")
                return handler403(request, "Access denied to procedure management")

            request.session['last_procedure_action'] = 'dashboard_access'
            request.session['procedure_access_time'] = timezone.now().isoformat()
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure management")