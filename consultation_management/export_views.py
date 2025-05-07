# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

# Python standard library imports
import csv
from datetime import datetime, timedelta
import logging

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Local application imports
from .models import Consultation, Prescription
from access_control.permissions import PermissionManager

# Initialize logger
logger = logging.getLogger(__name__)

class ConsultationExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'consultation_management')

    def get_filtered_queryset(self):
        """Get filtered queryset based on request parameters"""
        try:
            queryset = Consultation.objects.select_related('patient', 'doctor').all()
            date_range = self.request.GET.get('date_range')
            start_date = self.request.GET.get('start_date')
            end_date = self.request.GET.get('end_date')

            if date_range == 'custom' and start_date and end_date:
                try:
                    start_datetime = timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                    end_datetime = timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    queryset = queryset.filter(scheduled_datetime__range=[start_datetime, end_datetime])
                except ValueError:
                    raise ValueError("Invalid date format")
            elif date_range:
                try:
                    days = int(date_range)
                    end_date = timezone.now()
                    start_date = end_date - timedelta(days=days)
                    queryset = queryset.filter(scheduled_datetime__range=[start_date, end_date])
                except ValueError:
                    raise ValueError("Invalid date range value")

            return queryset.order_by('-scheduled_datetime')

        except Exception as e:
            logger.error(f"Error filtering consultations: {str(e)}")
            raise

    def export_csv(self, queryset):
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="consultations_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Consultation ID',
                'Patient Name',
                'Patient ID',
                'Doctor Name',
                'Type',
                'Status',
                'Scheduled Date',
                'Start Time',
                'End Time',
                'Duration (min)',
                'Chief Complaint',
                'Diagnosis',
                'Prescription Count',
                'Follow-up Date'
            ])

            for consultation in queryset:
                writer.writerow([
                    consultation.id,
                    consultation.patient.get_full_name(),
                    consultation.patient.id,
                    f"Dr. {consultation.doctor.get_full_name()}",
                    consultation.get_consultation_type_display(),
                    consultation.get_status_display(),
                    consultation.scheduled_datetime.strftime('%Y-%m-%d'),
                    consultation.actual_start_time.strftime('%H:%M') if consultation.actual_start_time else 'N/A',
                    consultation.actual_end_time.strftime('%H:%M') if consultation.actual_end_time else 'N/A',
                    consultation.duration_minutes,
                    consultation.chief_complaint,
                    consultation.diagnosis,
                    consultation.prescriptions.count(),
                    consultation.follow_up_date.strftime('%Y-%m-%d') if consultation.follow_up_date else 'N/A'
                ])

            return response
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {str(e)}")
            raise

    def export_pdf(self, queryset):
        try:
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="consultations_export.pdf"'

            doc = SimpleDocTemplate(response, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Title
            elements.append(Paragraph('Consultation Report', styles['Heading1']))
            elements.append(Spacer(1, 20))

            # Date Range Info
            date_range = self.request.GET.get('date_range')
            if date_range == 'custom':
                date_info = f"Custom Range: {self.request.GET.get('start_date')} to {self.request.GET.get('end_date')}"
            else:
                date_info = f"Last {date_range} days"
            elements.append(Paragraph(f"Period: {date_info}", styles['Normal']))
            elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 20))

            # Summary Statistics
            stats = [
                ['Total Consultations:', str(queryset.count())],
                ['Completed:', str(queryset.filter(status='COMPLETED').count())],
                ['Scheduled:', str(queryset.filter(status='SCHEDULED').count())],
                ['In Progress:', str(queryset.filter(status='IN_PROGRESS').count())]
            ]

            stats_table = Table(stats, colWidths=[120, 100])
            stats_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 20))

            # Main Consultations Table
            data = [[
                'Patient',
                'Doctor',
                'Type',
                'Status',
                'Date',
                'Duration'
            ]]

            for consultation in queryset:
                data.append([
                    consultation.patient.get_full_name(),
                    f"Dr. {consultation.doctor.get_full_name()}",
                    consultation.get_consultation_type_display(),
                    consultation.get_status_display(),
                    consultation.scheduled_datetime.strftime('%Y-%m-%d'),
                    f"{consultation.duration_minutes} min"
                ])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))

            elements.append(table)
            doc.build(elements)
            return response

        except Exception as e:
            logger.error(f"Error exporting PDF: {str(e)}")
            raise

    def get(self, request):
        try:
            # Get filtered queryset
            queryset = self.get_filtered_queryset()
            
            # Get export format
            export_format = request.GET.get('format', 'csv').lower()
            
            if export_format == 'csv':
                return self.export_csv(queryset)
            elif export_format == 'pdf':
                return self.export_pdf(queryset)
            else:
                messages.error(request, "Invalid export format specified")
                return redirect('consultation_dashboard')
                
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('consultation_dashboard')
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            messages.error(request, "An error occurred during export")
            return redirect('consultation_dashboard')

class ConsultationDetailExportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation.objects.select_related(
                'patient', 
                'doctor',
                'private_notes',
                'treatment_plan',
                'staff_instructions'
            ).prefetch_related(
                'prescriptions__items__medication',
                'phototherapy_sessions'
            ), pk=pk)

            export_format = request.GET.get('format', 'pdf')

            if export_format == 'pdf':
                return self._export_pdf(consultation)
            elif export_format == 'csv':
                return self._export_csv(consultation)
            else:
                messages.error(request, "Invalid export format")
                return redirect('consultation_detail', pk=pk)

        except Exception as e:
            logger.error(f"Error exporting consultation detail: {str(e)}")
            messages.error(request, "Error exporting consultation details")
            return redirect('consultation_detail', pk=pk)

    def _export_pdf(self, consultation):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="consultation_{consultation.id}_detail.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Clinic Header
        elements.append(Paragraph('Vitiligo PMS Clinic', styles['Heading1']))
        elements.append(Spacer(1, 20))

        # Basic Consultation Info
        elements.append(Paragraph('Consultation Details', styles['Heading2']))
        elements.append(Paragraph(f"ID: {consultation.id}", styles['Normal']))
        elements.append(Paragraph(f"Date: {consultation.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"Status: {consultation.get_status_display()}", styles['Normal']))
        elements.append(Paragraph(f"Type: {consultation.get_consultation_type_display()}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Patient Information
        elements.append(Paragraph('Patient Information', styles['Heading2']))
        patient_data = [
            ['Name', f"{consultation.patient.get_full_name()}"],
            ['Email', consultation.patient.email],
            ['Phone', consultation.patient.phone_number],
            ['Gender', consultation.patient.get_gender_display()]
        ]
        elements.append(Table(patient_data, colWidths=[100, 400]))
        elements.append(Spacer(1, 20))

        # Doctor Information
        elements.append(Paragraph('Doctor Information', styles['Heading2']))
        doctor_data = [
            ['Name', f"Dr. {consultation.doctor.get_full_name()}"],
            ['Email', consultation.doctor.email],
            ['Phone', consultation.doctor.phone_number]
        ]
        elements.append(Table(doctor_data, colWidths=[100, 400]))
        elements.append(Spacer(1, 20))

        # Clinical Information
        elements.append(Paragraph('Clinical Information', styles['Heading2']))
        if consultation.vitals:
            elements.append(Paragraph('Vitals:', styles['Heading3']))
            vitals_data = [[k, v] for k, v in consultation.vitals.items()]
            elements.append(Table(vitals_data, colWidths=[100, 400]))
        elements.append(Paragraph(f"Chief Complaint: {consultation.chief_complaint}", styles['Normal']))
        elements.append(Paragraph(f"Symptoms: {consultation.symptoms}", styles['Normal']))
        elements.append(Paragraph(f"Diagnosis: {consultation.diagnosis}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Add Patient Instructions
        elements.append(Paragraph('Patient Instructions', styles['Heading2']))
        if consultation.patient_instructions or consultation.lifestyle_instructions or consultation.care_instructions:
            if consultation.patient_instructions:
                elements.append(Paragraph("General Instructions:", styles['Heading3']))
                elements.append(Paragraph(consultation.patient_instructions, styles['Normal']))
                elements.append(Spacer(1, 10))
            
            if consultation.lifestyle_instructions:
                elements.append(Paragraph("Lifestyle & Dietary Instructions:", styles['Heading3']))
                elements.append(Paragraph(consultation.lifestyle_instructions, styles['Normal']))
                elements.append(Spacer(1, 10))
            
            if consultation.care_instructions:
                elements.append(Paragraph("Care & Precautions:", styles['Heading3']))
                elements.append(Paragraph(consultation.care_instructions, styles['Normal']))
        else:
            elements.append(Paragraph("No patient instructions provided", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Doctor's Notes
        if consultation.private_notes:
            elements.append(Paragraph("Doctor's Notes", styles['Heading2']))
            elements.append(Paragraph(f"Clinical Observations: {consultation.private_notes.clinical_observations}", styles['Normal']))
            elements.append(Paragraph(f"Differential Diagnosis: {consultation.private_notes.differential_diagnosis}", styles['Normal']))
            elements.append(Paragraph(f"Treatment Rationale: {consultation.private_notes.treatment_rationale}", styles['Normal']))
            elements.append(Spacer(1, 20))

        # Prescriptions
        if consultation.prescriptions.exists():
            elements.append(Paragraph('Prescriptions', styles['Heading2']))
            for prescription in consultation.prescriptions.all():
                elements.append(Paragraph(f'Prescription #{prescription.id}', styles['Heading3']))
                prescription_data = [['Medication', 'Dosage', 'Frequency', 'Duration']]
                for item in prescription.items.all():
                    prescription_data.append([
                        item.medication.name,
                        item.dosage,
                        item.frequency,
                        item.duration
                    ])
                elements.append(Table(prescription_data, colWidths=[150, 100, 100, 150]))
                elements.append(Spacer(1, 10))

        # Build and return PDF
        doc.build(elements)
        return response

    def _export_csv(self, consultation):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="consultation_{consultation.id}_detail.csv"'
        writer = csv.writer(response)

        # Basic Info
        writer.writerow(['Consultation Details'])
        writer.writerow(['ID', 'Date', 'Status', 'Type'])
        writer.writerow([
            consultation.id,
            consultation.scheduled_datetime.strftime('%Y-%m-%d %H:%M'),
            consultation.get_status_display(),
            consultation.get_consultation_type_display()
        ])
        writer.writerow([])

        # Patient Info
        writer.writerow(['Patient Information'])
        writer.writerow(['Name', consultation.patient.get_full_name()])
        writer.writerow(['Email', consultation.patient.email])
        writer.writerow(['Phone', consultation.patient.phone_number])
        writer.writerow([])

        # Clinical Info
        writer.writerow(['Clinical Information'])
        if consultation.vitals:
            writer.writerow(['Vitals'])
            for k, v in consultation.vitals.items():
                writer.writerow([k, v])
        writer.writerow(['Chief Complaint', consultation.chief_complaint])
        writer.writerow(['Symptoms', consultation.symptoms])
        writer.writerow(['Diagnosis', consultation.diagnosis])
        writer.writerow([])

        # Patient Instructions
        writer.writerow(['Patient Instructions'])
        writer.writerow(['General Instructions', consultation.patient_instructions or 'Not provided'])
        writer.writerow(['Lifestyle & Dietary Instructions', consultation.lifestyle_instructions or 'Not provided'])
        writer.writerow(['Care & Precautions', consultation.care_instructions or 'Not provided'])
        writer.writerow([])

        # Prescriptions
        if consultation.prescriptions.exists():
            writer.writerow(['Prescriptions'])
            for prescription in consultation.prescriptions.all():
                writer.writerow([f'Prescription #{prescription.id}'])
                writer.writerow(['Medication', 'Dosage', 'Frequency', 'Duration'])
                for item in prescription.items.all():
                    writer.writerow([
                        item.medication.name,
                        item.dosage,
                        item.frequency,
                        item.duration
                    ])
                writer.writerow([])

        return response

class PrescriptionDeleteView(LoginRequiredMixin, View):
    def post(self, request, consultation_id, prescription_id):
        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            prescription = get_object_or_404(Prescription, id=prescription_id, consultation=consultation)
            
            if not PermissionManager.check_module_delete(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to delete prescriptions")
                return redirect('consultation_detail', pk=consultation_id)

            with transaction.atomic():
                prescription.delete()
                messages.success(request, "Prescription deleted successfully")
                logger.info(f"Prescription {prescription_id} deleted from consultation {consultation_id}")

            return redirect('consultation_detail', pk=consultation_id)

        except Exception as e:
            logger.error(f"Error deleting prescription: {str(e)}")
            messages.error(request, "An error occurred while deleting the prescription")
            return redirect('consultation_detail', pk=consultation_id)

class PrescriptionExportView(LoginRequiredMixin, View):
    def get(self, request, prescription_id):
        try:
            prescription = get_object_or_404(Prescription.objects.select_related(
                'consultation__patient',
                'consultation__doctor'
            ).prefetch_related('items__medication'), id=prescription_id)

            export_format = request.GET.get('format', 'pdf')

            if export_format == 'pdf':
                return self._export_pdf(prescription)
            elif export_format == 'csv':
                return self._export_csv(prescription)
            else:
                messages.error(request, "Invalid export format")
                return redirect('prescription_dashboard')

        except Exception as e:
            logger.error(f"Error exporting prescription: {str(e)}")
            messages.error(request, "Error exporting prescription")
            return redirect('prescription_dashboard')

    def _export_pdf(self, prescription):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'

        # Create the PDF object using ReportLab
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Add hospital/clinic header
        elements.append(Paragraph('Your Clinic Name', styles['Heading1']))
        elements.append(Paragraph('Address Line 1<br/>Address Line 2<br/>Phone: XXX-XXX-XXXX', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Add prescription details
        elements.append(Paragraph(f'Prescription #{prescription.id}', styles['Heading2']))
        elements.append(Paragraph(f'Date: {prescription.created_at.strftime("%Y-%m-%d")}', styles['Normal']))
        elements.append(Spacer(1, 10))

        # Patient and Doctor info
        elements.append(Paragraph('Patient Details:', styles['Heading3']))
        elements.append(Paragraph(f"Name: {prescription.consultation.patient.get_full_name()}", styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('Doctor:', styles['Heading3']))
        elements.append(Paragraph(f"Dr. {prescription.consultation.doctor.get_full_name()}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Medications table
        data = [['Medication', 'Dosage', 'Frequency', 'Duration']]
        for item in prescription.items.all():
            data.append([
                item.medication.name,
                item.dosage,
                item.frequency,
                item.duration
            ])

        table = Table(data, colWidths=[*[doc.width/4]*4])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Add notes if any
        if prescription.notes:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph('Notes:', styles['Heading3']))
            elements.append(Paragraph(prescription.notes, styles['Normal']))

        # Build and return the PDF
        doc.build(elements)
        return response

    def _export_csv(self, prescription):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Prescription Details'])
        writer.writerow(['ID', 'Date', 'Patient', 'Doctor'])
        writer.writerow([
            prescription.id,
            prescription.created_at.strftime("%Y-%m-%d"),
            prescription.consultation.patient.get_full_name(),
            f"Dr. {prescription.consultation.doctor.get_full_name()}"
        ])
        writer.writerow([])
        writer.writerow(['Medications'])
        writer.writerow(['Name', 'Dosage', 'Frequency', 'Duration'])
        for item in prescription.items.all():
            writer.writerow([
                item.medication.name,
                item.dosage,
                item.frequency,
                item.duration
            ])

        if prescription.notes:
            writer.writerow([])
            writer.writerow(['Notes'])
            writer.writerow([prescription.notes])

        return response

class PrescriptionDashboardExportView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get all prescriptions with related data
            prescriptions = Prescription.objects.select_related(
                'consultation__patient',
                'consultation__doctor'
            ).prefetch_related('items__medication').all()

            # Get export format from query params
            export_format = request.GET.get('format', 'pdf')

            if export_format == 'pdf':
                return self._export_pdf(prescriptions)
            elif export_format == 'csv':
                return self._export_csv(prescriptions)
            else:
                messages.error(request, "Invalid export format")
                return redirect('prescription_dashboard')

        except Exception as e:
            logger.error(f"Error exporting prescription dashboard: {str(e)}")
            messages.error(request, "Error exporting prescriptions")
            return redirect('prescription_dashboard')

    def _export_pdf(self, prescriptions):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="prescriptions_report.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title and Header
        elements.append(Paragraph('Prescriptions Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        total_count = prescriptions.count()
        today = timezone.now()
        recent_count = prescriptions.filter(created_at__gte=today - timedelta(days=7)).count()

        stats = [
            ['Total Prescriptions:', str(total_count)],
            ['Recent (7 days):', str(recent_count)],
        ]

        stats_table = Table(stats, colWidths=[120, 100])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

        # Main Prescriptions Table
        data = [['Date', 'Patient', 'Doctor', 'Medications']]

        for prescription in prescriptions:
            medications = ", ".join([item.medication.name for item in prescription.items.all()])
            data.append([
                prescription.created_at.strftime("%Y-%m-%d"),
                prescription.consultation.patient.get_full_name(),
                f"Dr. {prescription.consultation.doctor.get_full_name()}",
                medications[:100] + "..." if len(medications) > 100 else medications
            ])

        table = Table(data, colWidths=[80, 120, 120, 180])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table)

        doc.build(elements)
        return response

    def _export_csv(self, prescriptions):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="prescriptions_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Patient', 'Doctor', 'Medications', 'Notes'])

        for prescription in prescriptions:
            medications = "; ".join([
                f"{item.medication.name} ({item.dosage}, {item.frequency}, {item.duration})"
                for item in prescription.items.all()
            ])
            writer.writerow([
                prescription.created_at.strftime("%Y-%m-%d"),
                prescription.consultation.patient.get_full_name(),
                f"Dr. {prescription.consultation.doctor.get_full_name()}",
                medications,
                prescription.notes
            ])

        return response