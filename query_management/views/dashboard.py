# Python Standard Library imports
import csv
import logging
from datetime import datetime, timedelta

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Django core imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.core.paginator import (
    EmptyPage,
    PageNotAnInteger,
    Paginator,
)
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    Q,
    fields,
)
from django.db.models.functions import (
    ExtractHour,
    TruncDate,
    TruncMonth,
    TruncWeek,
)
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic.edit import CreateView

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import (
    handler403,
    handler404,
    handler500,
)
from patient_management.models import Patient

# Current app imports
from ..forms import QueryCreateForm
from ..models import (
    Query,
    QueryAttachment,
    QueryTag,
    QueryUpdate,
)
from ..utils import (
    get_template_path,
    send_query_notification,
)

# Logger configuration
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()

class QueryManagementView(LoginRequiredMixin, View):
    def get_query_trend_data(self, queryset, days=30):
        """Calculate query volume trend data"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        daily_counts = (queryset
            .filter(created_at__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('query_id'))
            .order_by('date'))

        dates = []
        counts = []
        
        current = start_date.date()
        while current <= end_date.date():
            dates.append(current.strftime('%Y-%m-%d'))
            count = next((item['count'] for item in daily_counts if item['date'] == current), 0)
            counts.append(count)
            current += timedelta(days=1)

        return {
            'labels': dates,
            'values': counts
        }

    def get_status_distribution(self, queryset):
        """Calculate query status distribution"""
        status_counts = (queryset
            .values('status')
            .annotate(count=Count('query_id'))
            .order_by('status'))

        status_map = dict(Query.STATUS_CHOICES)
        return {
            'labels': [status_map.get(item['status'], item['status']) for item in status_counts],
            'values': [item['count'] for item in status_counts]
        }

    def get_response_time_data(self, queryset, period='day'):
        """Calculate average response times"""
        if period == 'week':
            trunc_fn = TruncWeek
        elif period == 'month':
            trunc_fn = TruncMonth
        else:  # day
            trunc_fn = TruncDate

        data = (queryset
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(avg_time=Avg('response_time'))
            .order_by('period'))
        
        return {
            'labels': [item['period'].strftime('%Y-%m-%d') for item in data],
            'values': [float(item['avg_time'].total_seconds()/3600) if item['avg_time'] else 0 for item in data]
        }

    def get_source_distribution(self, queryset):
        """Calculate query source distribution"""
        source_counts = (queryset
            .values('source')
            .annotate(count=Count('query_id'))
            .order_by('-count'))

        source_map = dict(Query.SOURCE_CHOICES)
        return {
            'labels': [source_map.get(item['source'], item['source']) for item in source_counts],
            'values': [item['count'] for item in source_counts]
        }

    def get_staff_performance(self, queryset, days=30):
        """Calculate staff performance metrics"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        data = (queryset
            .filter(created_at__gte=start_date)
            .values('assigned_to__first_name', 'assigned_to__last_name')
            .annotate(
                total_queries=Count('query_id'),
                resolved_queries=Count('query_id', filter=Q(status='RESOLVED')),
                avg_response_time=Avg('response_time')
            )
            .exclude(assigned_to=None)
            .order_by('-total_queries'))

        return {
            'labels': [f"{item['assigned_to__first_name']} {item['assigned_to__last_name']}" for item in data],
            'total_queries': [item['total_queries'] for item in data],
            'resolved_queries': [item['resolved_queries'] for item in data]
        }

    def get_conversion_metrics(self, queryset):
        """Calculate conversion metrics"""
        total = queryset.count()
        converted = queryset.filter(conversion_status=True).count()
        conversion_rate = (converted / total * 100) if total > 0 else 0

        return {
            'total_converted': converted,
            'total_pending': total - converted,
            'conversion_rate': round(conversion_rate, 1)
        }

    def get(self, request):
        try:
            # Check module access permission
            if not PermissionManager.check_module_access(request.user, 'query_management'):
                messages.error(request, "You don't have permission to access Query Management")
                return handler403(request, exception="Access Denied")

            template_path = get_template_path('dashboard/dashboard.html', request.user.role, 'query_management')
            
            if not template_path:
                return HttpResponse("Unauthorized access", status=403)

            # Get base queryset
            queryset = Query.objects.select_related(
                'user', 
                'assigned_to'
            ).prefetch_related(
                'tags',
                'updates',
                'attachments'
            )
            
            # Get filter parameters
            priority = request.GET.get('priority')
            status = request.GET.get('status')
            source = request.GET.get('source')
            search_query = request.GET.get('search')

            # Apply filters
            if priority:
                queryset = queryset.filter(priority=priority)
            if status:
                queryset = queryset.filter(status=status)
            if source:
                queryset = queryset.filter(source=source)
            
            # Apply search
            if search_query:
                queryset = queryset.filter(
                    Q(subject__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(query_id__icontains=search_query) |
                    Q(user__first_name__icontains=search_query) |
                    Q(user__last_name__icontains=search_query) |
                    Q(contact_email__icontains=search_query) |
                    Q(contact_phone__icontains=search_query)
                )

            # Pagination
            paginator = Paginator(queryset, 10)
            page = request.GET.get('page', 1)
            try:
                queries = paginator.page(page)
            except PageNotAnInteger:
                queries = paginator.page(1)
            except EmptyPage:
                queries = paginator.page(paginator.num_pages)

            # Get choices for dropdowns
            status_choices = Query.STATUS_CHOICES
            source_choices = Query.SOURCE_CHOICES

            # Get available staff members for assignment - Updated to use Role model correctly
            User = get_user_model()
            staff_roles = Role.objects.filter(name__in=['ADMIN', 'DOCTOR', 'NURSE', 'STAFF', 'MANAGER'])
            available_staff = User.objects.filter(
                is_active=True,
                role__in=staff_roles
            ).order_by('first_name')

            # Calculate statistics
            current_date = timezone.now()
            start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            resolved_this_month = Query.objects.filter(resolved_at__gte=start_of_month).count()
            total_queries = Query.objects.count()

            context = {
                'queries': queries,
                'total_queries': total_queries,
                'open_queries': Query.objects.filter(
                    status__in=['NEW', 'IN_PROGRESS', 'WAITING']
                ).count(),
                'resolved_this_month': resolved_this_month,
                'resolution_rate': round((resolved_this_month / total_queries * 100) if total_queries > 0 else 0, 1),
                'status_choices': status_choices,
                'source_choices': source_choices,
                'current_filters': {
                    'priority': priority or '',
                    'status': status or '',
                    'source': source or '',
                    'search': search_query or '',
                },
                'paginator': paginator,
                'page_obj': queries,
                'available_staff': available_staff,
            }

            # Prepare graph data
            context.update({
                'query_trend_data': self.get_query_trend_data(queryset),
                'status_distribution': self.get_status_distribution(queryset),
                'response_time_data': self.get_response_time_data(
                    queryset, 
                    request.GET.get('response_time_period', 'day')
                ),
                'source_distribution': self.get_source_distribution(queryset),
                'staff_performance': self.get_staff_performance(queryset),
                'conversion_metrics': self.get_conversion_metrics(queryset),
                'periods': [
                    ('7', 'Last 7 Days'),
                    ('30', 'Last 30 Days'),
                    ('90', 'Last 90 Days'),
                    ('custom', 'Custom Range'),
                ],
            })

            # Error handling for graph data
            if not any([
                context['query_trend_data']['values'],
                context['status_distribution']['values'],
                context['source_distribution']['values']
            ]):
                messages.info(request, "Not enough data available for some visualizations")

            return render(request, template_path, context)
            
        except Exception as e:
            logger.error(f"Error in QueryManagementView: {str(e)}", exc_info=True)
            return handler500(request, exception=str(e))