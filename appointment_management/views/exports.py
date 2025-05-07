# Python Standard Library imports
import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
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
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.views.generic.edit import FormView

# Django REST Framework imports
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from doctor_management.models import DoctorProfile
from error_handling.views import handler403, handler404, handler500
from patient_management.models import MedicalHistory

from ..utils import get_template_path
from ..forms import AppointmentCreateForm
from ..models import (
    Appointment,
    AppointmentReminder,
    CancellationReason,
    DoctorTimeSlot,
    ReminderConfiguration,
    ReminderTemplate,
)

# Logger configuration
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()

class AppointmentExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'appointment_management')

    def get_filtered_queryset(self, date_range, start_date=None, end_date=None):
        """Filter queryset based on date range"""
        queryset = Appointment.objects.select_related('patient', 'doctor', 'time_slot')

        if date_range == 'custom':
            if not start_date or not end_date:
                raise ValueError("Both start date and end date are required for custom range")
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(date__range=[start_datetime, end_datetime])
            except ValueError as e:
                raise ValueError(f"Invalid date format: {str(e)}")
        else:
            try:
                days = int(date_range or '30')
                if days <= 0:
                    raise ValueError("Days must be a positive number")
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=days)
                queryset = queryset.filter(date__range=[start_date, end_date])
            except ValueError:
                raise ValueError("Invalid date range value")

        return queryset

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'csv')
            date_range = request.GET.get('date_range')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            queryset = self.get_filtered_queryset(date_range, start_date, end_date)

            if export_format == 'csv':
                return self.export_csv(queryset)
            elif export_format == 'pdf':
                return self.export_pdf(queryset)
            else:
                messages.error(request, "Invalid export format")
                return redirect('appointment_dashboard')

        except Exception as e:
            messages.error(request, f"Export failed: {str(e)}")
            return redirect('appointment_dashboard')

    def export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="appointments_report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Appointment ID',
            'Patient Name',
            'Doctor Name',
            'Date',
            'Time',
            'Type',
            'Status',
            'Priority',
            'Notes',
            'Created At',
            'Last Updated',
            'Cancellation Reason'
        ])

        for appointment in queryset:
            cancellation_reason = appointment.cancellation_reason.reason if hasattr(appointment, 'cancellation_reason') else 'N/A'
            writer.writerow([
                appointment.id,
                appointment.patient.get_full_name(),
                appointment.doctor.get_full_name(),
                appointment.date,
                appointment.time_slot.start_time if appointment.time_slot else 'N/A',
                appointment.get_appointment_type_display(),
                appointment.get_status_display(),
                appointment.get_priority_display(),
                appointment.notes or 'N/A',
                appointment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                appointment.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                cancellation_reason
            ])

        return response

    def export_pdf(self, queryset):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="appointments_report.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        # Title
        elements.append(Paragraph('Appointments Report', title_style))
        elements.append(Spacer(1, 20))

        # Statistics
        stats = [
            ['Total Appointments:', str(queryset.count())],
            ['Pending Appointments:', str(queryset.filter(status='PENDING').count())],
            ['Completed Appointments:', str(queryset.filter(status='COMPLETED').count())],
            ['Cancelled Appointments:', str(queryset.filter(status='CANCELLED').count())]
        ]

        stats_table = Table(stats, colWidths=[150, 100])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),  # Changed from colors.grey
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

        # Appointments table
        data = [['Date', 'Time', 'Patient', 'Doctor', 'Type', 'Status']]
        for appointment in queryset:
            data.append([
                appointment.date.strftime('%Y-%m-%d'),
                appointment.time_slot.start_time.strftime('%H:%M') if appointment.time_slot else 'N/A',
                appointment.patient.get_full_name(),
                appointment.doctor.get_full_name(),
                appointment.get_appointment_type_display(),
                appointment.get_status_display()
            ])

        table = Table(data, colWidths=[70, 50, 100, 100, 80, 80])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),  # Light gray background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Changed text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        doc.build(elements)
        return response
    

class AppointmentExportSingleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'appointment_management')

    def get(self, request, appointment_id):
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            export_format = request.GET.get('format', 'csv')

            if export_format == 'csv':
                return self.export_csv(appointment)
            elif export_format == 'pdf':
                return self.export_pdf(appointment)
            else:
                messages.error(request, "Invalid export format")
                return redirect('appointment_dashboard')

        except Exception as e:
            messages.error(request, f"Export failed: {str(e)}")
            return redirect('appointment_dashboard')

    def export_csv(self, appointment):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="appointment_{appointment.id}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Appointment ID',
            'Patient Name',
            'Doctor Name',
            'Date',
            'Time',
            'Type',
            'Status',
            'Priority',
            'Notes',
            'Created At',
            'Last Updated',
            'Cancellation Reason'
        ])

        # Get cancellation reason if exists
        cancellation_reason = appointment.cancellation_reason.reason if hasattr(appointment, 'cancellation_reason') else 'N/A'

        writer.writerow([
            appointment.id,
            appointment.patient.get_full_name(),
            appointment.doctor.get_full_name(),
            appointment.date,
            appointment.time_slot.start_time if appointment.time_slot else 'N/A',
            appointment.get_appointment_type_display(),
            appointment.get_status_display(),
            appointment.get_priority_display(),
            appointment.notes or 'N/A',
            appointment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            appointment.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            cancellation_reason
        ])

        return response

    def export_pdf(self, appointment):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="appointment_{appointment.id}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']

        # Title
        elements.append(Paragraph(f'Appointment Details - #{appointment.id}', title_style))
        elements.append(Spacer(1, 20))

        # Basic Info
        elements.append(Paragraph('Basic Information', subtitle_style))
        elements.append(Spacer(1, 10))

        data = [
            ['Patient Name:', appointment.patient.get_full_name()],
            ['Doctor Name:', appointment.doctor.get_full_name()],
            ['Date:', appointment.date.strftime('%B %d, %Y')],
            ['Time:', appointment.time_slot.start_time.strftime('%I:%M %p') if appointment.time_slot else 'N/A'],
            ['Type:', appointment.get_appointment_type_display()],
            ['Status:', appointment.get_status_display()],
            ['Priority:', appointment.get_priority_display()]
        ]

        # Create table for basic info
        table = Table(data, colWidths=[120, 300])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Notes Section
        if appointment.notes:
            elements.append(Paragraph('Notes', subtitle_style))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(appointment.notes, normal_style))
            elements.append(Spacer(1, 20))

        # Cancellation Info
        if hasattr(appointment, 'cancellation_reason'):
            elements.append(Paragraph('Cancellation Information', subtitle_style))
            elements.append(Spacer(1, 10))
            cancel_data = [
                ['Reason:', appointment.cancellation_reason.reason],
                ['Cancelled By:', appointment.cancellation_reason.cancelled_by.get_full_name()],
                ['Cancelled At:', appointment.cancellation_reason.cancelled_at.strftime('%B %d, %Y %I:%M %p')]
            ]
            cancel_table = Table(cancel_data, colWidths=[120, 300])
            cancel_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(cancel_table)

        doc.build(elements)
        return response