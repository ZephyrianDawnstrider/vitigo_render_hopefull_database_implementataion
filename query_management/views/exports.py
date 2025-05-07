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

class QueryExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """
        Verify if the user has permission to export queries
        """
        return PermissionManager.check_module_access(self.request.user, 'query_management')

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(self.request.user, 'query_management'):
            messages.error(request, "You don't have permission to export queries")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'csv')
            date_range = request.GET.get('date_range')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            # Get queryset based on date range
            try:
                queryset = self.get_filtered_queryset(date_range, start_date, end_date)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('query_management')

            if export_format == 'csv':
                return self.export_csv(queryset)
            elif export_format == 'pdf':
                return self.export_pdf(queryset)
            else:
                messages.error(request, "Invalid export format")
                return redirect('query_management')
        except Exception as e:
            messages.error(request, f"Export failed: {str(e)}")
            return redirect('query_management')

    def get_filtered_queryset(self, date_range, start_date=None, end_date=None):
        """
        Filter queryset based on date range or custom dates
        """
        queryset = Query.objects.all()

        if date_range == 'custom':
            if not start_date or not end_date:
                raise ValueError("Both start date and end date are required for custom range")
            try:
                # Convert date strings from datepicker format (MM/DD/YYYY) to datetime
                start_datetime = datetime.strptime(start_date, '%m/%d/%Y')
                end_datetime = datetime.strptime(end_date, '%m/%d/%Y')
                
                # Add time to make end_date inclusive
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                
                # Convert to timezone-aware datetime
                start_datetime = timezone.make_aware(start_datetime)
                end_datetime = timezone.make_aware(end_datetime)
                
                if start_datetime > end_datetime:
                    raise ValueError("Start date must be before end date")
                
                queryset = queryset.filter(created_at__range=[start_datetime, end_datetime])
            except ValueError as e:
                raise ValueError(f"Invalid date format: {str(e)}")
        else:
            try:
                days = int(date_range or '30')  # Default to 30 days if not specified
                if days <= 0:
                    raise ValueError("Days must be a positive number")
                    
                end_date = timezone.now()
                start_date = end_date - timedelta(days=days)
                queryset = queryset.filter(created_at__range=[start_date, end_date])
            except ValueError:
                raise ValueError("Invalid date range value")

        return queryset.select_related('user', 'assigned_to')

    def get_user_details(self, user):
        """Helper method to get formatted user details"""
        if not user:
            return "N/A"
        return f"{user.get_full_name()} ({user.email})"

    def format_duration(self, duration):
        """Helper method to format duration"""
        if not duration:
            return "N/A"
        total_seconds = duration.total_seconds()
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        parts = []
        if days:
            parts.append(f"{int(days)}d")
        if hours:
            parts.append(f"{int(hours)}h")
        if minutes:
            parts.append(f"{int(minutes)}m")
            
        return " ".join(parts) if parts else "0m"

    def get_duration_in_hours(self, duration):
        """Helper method to get duration in hours for statistics"""
        if not duration:
            return 0
        return duration.total_seconds() / 3600

    def export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="detailed_query_report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Query ID',
            'Subject',
            'Description',
            'Status',
            'Priority',
            'Source',
            'Query Type',
            'Created At',
            'Updated At',
            'Resolved At',
            'Response Time',
            'Assigned To',
            'User/Contact',
            'Contact Email',
            'Contact Phone',
            'Is Anonymous',
            'Is Patient',
            'Expected Response Date',
            'Follow Up Date',
            'Resolution Summary',
            'Satisfaction Rating',
            'Conversion Status',
            'Tags',
            'Total Updates',
            'Total Attachments'
        ])

        for query in queryset:
            writer.writerow([
                query.query_id,
                query.subject,
                query.description[:100] + '...' if len(query.description) > 100 else query.description,
                query.get_status_display(),
                query.get_priority_display(),
                query.get_source_display(),
                query.get_query_type_display() if query.query_type else 'N/A',
                query.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                query.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                query.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if query.resolved_at else 'N/A',
                self.format_duration(query.response_time),
                self.get_user_details(query.assigned_to),
                self.get_user_details(query.user) if not query.is_anonymous else 'Anonymous',
                query.contact_email or 'N/A',
                query.contact_phone or 'N/A',
                'Yes' if query.is_anonymous else 'No',
                'Yes' if query.is_patient else 'No',
                query.expected_response_date.strftime('%Y-%m-%d %H:%M:%S') if query.expected_response_date else 'N/A',
                query.follow_up_date.strftime('%Y-%m-%d %H:%M:%S') if query.follow_up_date else 'N/A',
                query.resolution_summary or 'N/A',
                f"{query.satisfaction_rating}/5" if query.satisfaction_rating else 'N/A',
                'Converted' if query.conversion_status else 'Not Converted',
                ', '.join(tag.name for tag in query.tags.all()) or 'No Tags',
                query.updates.count(),
                query.attachments.count()
            ])

        return response

    def export_pdf(self, queryset):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="detailed_query_report.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']

        # Title
        elements.append(Paragraph('Detailed Query Management Report', title_style))
        elements.append(Spacer(1, 20))

        # Export timestamp
        elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 20))

        # Statistics summary
        avg_response_time = queryset.filter(response_time__isnull=False).aggregate(Avg('response_time'))['response_time__avg']
        avg_response_hours = self.get_duration_in_hours(avg_response_time) if avg_response_time else 0

        stats = [
            ['Total Queries:', str(queryset.count())],
            ['Open Queries:', str(queryset.filter(status__in=['NEW', 'IN_PROGRESS', 'WAITING']).count())],
            ['Resolved Queries:', str(queryset.filter(status='RESOLVED').count())],
            ['Average Response Time:', f"{avg_response_hours:.1f} hours"]
        ]
        
        stats_table = Table(stats, colWidths=[150, 200])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

        # Detailed Query List
        elements.append(Paragraph('Detailed Query List', heading_style))
        elements.append(Spacer(1, 10))

        for query in queryset:
            # Query header
            elements.append(Paragraph(f"Query #{query.query_id}: {query.subject}", styles['Heading3']))
            
            # Query details
            details = [
                ['Status:', query.get_status_display(), 'Priority:', query.get_priority_display()],
                ['Created:', query.created_at.strftime('%Y-%m-%d %H:%M:%S'), 'Source:', query.get_source_display()],
                ['Assigned To:', self.get_user_details(query.assigned_to), 'Response Time:', self.format_duration(query.response_time)],
                ['User/Contact:', self.get_user_details(query.user) if not query.is_anonymous else 'Anonymous', 'Type:', query.get_query_type_display() or 'N/A']
            ]
            
            detail_table = Table(details, colWidths=[80, 150, 80, 150])
            detail_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(detail_table)
            elements.append(Spacer(1, 10))

            # Description
            elements.append(Paragraph('Description:', styles['Heading4']))
            elements.append(Paragraph(query.description, normal_style))
            elements.append(Spacer(1, 10))

            # Additional details in a smaller table
            if query.resolution_summary or query.satisfaction_rating or query.tags.exists():
                additional_info = []
                if query.resolution_summary:
                    additional_info.append(['Resolution:', query.resolution_summary])
                if query.satisfaction_rating:
                    additional_info.append(['Satisfaction:', f"{query.satisfaction_rating}/5"])
                if query.tags.exists():
                    additional_info.append(['Tags:', ', '.join(tag.name for tag in query.tags.all())])
                
                add_table = Table(additional_info, colWidths=[80, 380])
                add_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(add_table)

            elements.append(Spacer(1, 20))

        doc.build(elements)
        return response