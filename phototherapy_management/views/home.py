from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.db.models import Sum, Avg
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import ListView
from datetime import timedelta
import logging
from phototherapy_management.models import HomePhototherapyLog, PhototherapyPlan
from access_control.permissions import PermissionManager
from phototherapy_management.utils import get_template_path
from error_handling.views import handler403
from django.db import models

logger = logging.getLogger(__name__)


class HomeTherapyLogsView(LoginRequiredMixin, ListView):
    model = HomePhototherapyLog
    context_object_name = 'therapy_logs'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'phototherapy_management'):
                logger.warning(f"Access denied to home therapy logs for user {request.user.id}")
                messages.error(request, "You don't have permission to access Home Therapy Logs")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in home therapy logs dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def get(self, request, *args, **kwargs):
        export_format = request.GET.get('export')
        if export_format in ['excel', 'pdf']:
            from .export import HomeTherapyLogsExportView
            export_view = HomeTherapyLogsExportView()
            return export_view.get(request)
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        try:
            return [get_template_path(
                'home_therapy/logs_list.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_home_therapy_logs.html']

    def get_queryset(self):
        try:
            queryset = HomePhototherapyLog.objects.select_related(
                'plan__patient',
                'plan__protocol__phototherapy_type'
            ).order_by('-date', '-time')

            # Search functionality
            search = self.request.GET.get('search', '')
            if search:
                queryset = queryset.filter(
                    Q(plan__patient__first_name__icontains=search) |
                    Q(plan__patient__last_name__icontains=search) |
                    Q(body_areas_treated__icontains=search) |
                    Q(notes__icontains=search)
                )

            # Date range filter
            start_date = self.request.GET.get('start_date')
            end_date = self.request.GET.get('end_date')
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)

            # Exposure type filter
            exposure_type = self.request.GET.get('exposure_type')
            if exposure_type:
                queryset = queryset.filter(exposure_type=exposure_type)

            return queryset
        except Exception as e:
            logger.error(f"Error in home therapy logs queryset: {str(e)}")
            return HomePhototherapyLog.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Filter values
            context['search'] = self.request.GET.get('search', '')
            context['start_date'] = self.request.GET.get('start_date', '')
            context['end_date'] = self.request.GET.get('end_date', '')
            context['exposure_type'] = self.request.GET.get('exposure_type', '')
            
            # Summary statistics
            queryset = self.get_queryset()
            context.update({
                'total_logs': queryset.count(),
                'total_duration': queryset.aggregate(
                    total=models.Sum('duration_minutes')
                )['total'] or 0,
                'unique_patients': queryset.values('plan__patient').distinct().count(),
                'exposure_choices': dict(HomePhototherapyLog.EXPOSURE_CHOICES),
                
                # Additional statistics
                'logs_this_month': queryset.filter(
                    date__month=timezone.now().month
                ).count(),
                'avg_duration': queryset.aggregate(
                    avg=models.Avg('duration_minutes')
                )['avg'] or 0,
                'compliance_percentage': self.calculate_compliance_percentage(queryset),
                
                # User permissions
                'can_export': PermissionManager.check_module_modify(
                    self.request.user, 'phototherapy_management'
                ),
            })
            
        except Exception as e:
            logger.error(f"Error getting home therapy logs context: {str(e)}")
            messages.error(self.request, "Error loading some log data")
        
        return context

    def calculate_compliance_percentage(self, queryset):
        try:
            # Group logs by patient and count sessions per week
            this_week = timezone.now().date() - timedelta(days=7)
            weekly_sessions = queryset.filter(
                date__gte=this_week
            ).values('plan__patient').annotate(
                sessions=Count('id')
            )

            if not weekly_sessions:
                return 0

            # Get required sessions per week from plans
            total_compliance = 0
            for patient_sessions in weekly_sessions:
                plan = PhototherapyPlan.objects.get(
                    patient_id=patient_sessions['plan__patient']
                )
                required = plan.protocol.frequency_per_week
                actual = patient_sessions['sessions']
                total_compliance += (actual / required) * 100 if required > 0 else 0

            return round(total_compliance / len(weekly_sessions))

        except Exception as e:
            logger.error(f"Error calculating compliance: {str(e)}")
            return 0