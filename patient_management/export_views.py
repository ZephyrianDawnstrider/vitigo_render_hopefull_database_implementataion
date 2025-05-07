import logging
from io import BytesIO
import xlsxwriter
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.db.models import Q
from django.contrib.auth import get_user_model

from access_control.models import Role
from user_management.models import CustomUser
from .models import Patient, MedicalHistory, VitiligoAssessment, TreatmentPlan, Medication

logger = logging.getLogger(__name__)
User = get_user_model()

class PatientDataExportView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        try:
            user = get_object_or_404(CustomUser, id=user_id)
            patient = get_object_or_404(Patient, user=user)
            export_format = request.GET.get('format', 'excel')
            
            if export_format == 'pdf':
                return self.export_pdf(user, patient)
            return self.export_excel(user, patient)
            
        except Exception as e:
            logger.error(f"Error exporting patient data: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def export_excel(self, user, patient):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})

        # Personal Information Sheet
        self._create_personal_info_sheet(workbook, user, patient, header_format, cell_format)
        
        # Medical History Sheet
        self._create_medical_history_sheet(workbook, patient, header_format, cell_format)
        
        # Assessments Sheet
        self._create_assessments_sheet(workbook, patient, header_format, cell_format)
        
        # Treatments Sheet
        self._create_treatments_sheet(workbook, patient, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=patient_data_{user.id}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        return response

    def _create_personal_info_sheet(self, workbook, user, patient, header_format, cell_format):
        sheet = workbook.add_worksheet('Personal Information')
        data = [
            ['Field', 'Value'],
            ['Full Name', user.get_full_name()],
            ['Email', user.email],
            ['Phone', f"{user.country_code} {user.phone_number}"],
            ['Gender', user.get_gender_display()],
            ['Date of Birth', patient.date_of_birth.strftime('%Y-%m-%d')],
            ['Blood Group', patient.blood_group],
            ['Address', patient.address],
            ['Emergency Contact', f"{patient.emergency_contact_name} ({patient.emergency_contact_number})"],
        ]
        
        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)

    def _create_medical_history_sheet(self, workbook, patient, header_format, cell_format):
        sheet = workbook.add_worksheet('Medical History')
        try:
            history = patient.medical_history
            data = [
                ['Category', 'Details'],
                ['Allergies', history.allergies],
                ['Chronic Conditions', history.chronic_conditions],
                ['Past Surgeries', history.past_surgeries],
                ['Family History', history.family_history],
            ]
        except MedicalHistory.DoesNotExist:
            data = [['No medical history available']]

        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)

    def _create_assessments_sheet(self, workbook, patient, header_format, cell_format):
        sheet = workbook.add_worksheet('Vitiligo Assessments')
        headers = ['Date', 'BSA Score', 'VASI Score', 'Notes']
        sheet.write_row(0, 0, headers, header_format)

        assessments = VitiligoAssessment.objects.filter(patient=patient).order_by('-assessment_date')
        for row, assessment in enumerate(assessments, start=1):
            sheet.write(row, 0, assessment.assessment_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, assessment.bsa_score, cell_format)
            sheet.write(row, 2, assessment.vasi_score, cell_format)
            sheet.write(row, 3, assessment.notes or '', cell_format)

    def _create_treatments_sheet(self, workbook, patient, header_format, cell_format):
        sheet = workbook.add_worksheet('Treatments & Medications')
        headers = ['Start Date', 'End Date', 'Treatment/Medication', 'Dosage', 'Notes']
        sheet.write_row(0, 0, headers, header_format)

        row = 1
        # Add treatments
        for treatment in TreatmentPlan.objects.filter(patient=patient).order_by('-created_date'):
            sheet.write(row, 0, treatment.created_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, treatment.end_date.strftime('%Y-%m-%d') if treatment.end_date else 'Ongoing', cell_format)
            sheet.write(row, 2, treatment.treatment_type, cell_format)
            sheet.write(row, 3, 'N/A', cell_format)
            sheet.write(row, 4, treatment.notes or '', cell_format)
            row += 1

        # Add medications
        for medication in Medication.objects.filter(patient=patient).order_by('-start_date'):
            sheet.write(row, 0, medication.start_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, medication.end_date.strftime('%Y-%m-%d') if medication.end_date else 'Ongoing', cell_format)
            sheet.write(row, 2, medication.name, cell_format)
            sheet.write(row, 3, medication.dosage, cell_format)
            sheet.write(row, 4, medication.notes or '', cell_format)
            row += 1

    def export_pdf(self, user, patient):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=patient_data_{user.id}_{datetime.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(f'Patient Data: {user.get_full_name()}', styles['Heading1']))
        elements.append(Spacer(1, 20))

        # Personal Information
        elements.append(Paragraph('Personal Information', styles['Heading2']))
        personal_data = [
            ['Field', 'Value'],
            ['Full Name', user.get_full_name()],
            ['Email', user.email],
            ['Phone', f"{user.country_code} {user.phone_number}"],
            ['Gender', user.get_gender_display()],
            ['Date of Birth', patient.date_of_birth.strftime('%Y-%m-%d')],
        ]
        personal_table = Table(personal_data, colWidths=[200, 300])
        personal_table.setStyle(self._get_table_style())
        elements.append(personal_table)
        elements.append(Spacer(1, 20))

        # Add other sections similarly...

        doc.build(elements)
        return response

    def _get_table_style(self):
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])

class PatientListExportView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            patient_role = Role.objects.get(name='PATIENT')
            patients = User.objects.filter(role=patient_role).select_related('patient_profile')
            
            # Apply any filters from the list view
            status = request.GET.get('status')
            search_query = request.GET.get('search')
            
            if status:
                patients = patients.filter(is_active=(status == 'active'))
            
            if search_query:
                patients = patients.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(patient_profile__phone_number__icontains=search_query)
                )
            
            if export_format == 'pdf':
                return self.export_pdf(patients)
            return self.export_excel(patients)
            
        except Exception as e:
            logger.error(f"Error exporting patient list: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def export_excel(self, patients):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'yyyy-mm-dd'
        })

        # Create Metrics sheet
        self._create_metrics_sheet(workbook, patients, header_format, cell_format)
        
        # Create Patients List sheet
        self._create_patients_sheet(workbook, patients, header_format, cell_format, date_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'patient_list_{datetime.now().strftime("%Y%m%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    def _create_metrics_sheet(self, workbook, patients, header_format, cell_format):
        sheet = workbook.add_worksheet('Metrics')
        
        # Calculate metrics
        total_patients = patients.count()
        active_patients = patients.filter(is_active=True).count()
        inactive_patients = patients.filter(is_active=False).count()
        new_this_month = patients.filter(
            date_joined__month=datetime.now().month,
            date_joined__year=datetime.now().year
        ).count()

        data = [
            ['Metric', 'Value'],
            ['Total Patients', total_patients],
            ['Active Patients', active_patients],
            ['Inactive Patients', inactive_patients],
            ['New Patients This Month', new_this_month],
            ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M')]
        ]
        
        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)

    def _create_patients_sheet(self, workbook, patients, header_format, cell_format, date_format):
        sheet = workbook.add_worksheet('Patient List')
        headers = ['ID', 'Name', 'Email', 'Phone', 'Gender', 'Status', 'Date Joined', 'Profile Status']
        
        # Set column widths
        widths = [10, 30, 40, 20, 15, 15, 20, 20]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, patient in enumerate(patients, start=1):
            try:
                profile = patient.patient_profile
                has_profile = "Complete"
            except Patient.DoesNotExist:
                profile = None
                has_profile = "Incomplete"

            data = [
                patient.id,
                patient.get_full_name(),
                patient.email,
                f"{patient.country_code} {patient.phone_number}" if patient.phone_number else 'N/A',
                patient.get_gender_display() or 'Not specified',
                'Active' if patient.is_active else 'Inactive',
                patient.date_joined,
                has_profile
            ]

            for col, value in enumerate(data):
                if col == 6:  # Date Joined column
                    sheet.write(row, col, value, date_format)
                else:
                    sheet.write(row, col, value, cell_format)

    def export_pdf(self, patients):
        response = HttpResponse(content_type='application/pdf')
        filename = f'patient_list_{datetime.now().strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename={filename}'

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Patient List Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Metrics Section
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        metrics_data = [
            ['Metric', 'Count'],
            ['Total Patients', str(patients.count())],
            ['Active Patients', str(patients.filter(is_active=True).count())],
            ['Inactive Patients', str(patients.filter(is_active=False).count())]
        ]
        metrics_table = Table(metrics_data, colWidths=[200, 100])
        metrics_table.setStyle(self._get_table_style())
        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Patients List
        elements.append(Paragraph('Patient List', styles['Heading2']))
        patient_data = [['Name', 'Email', 'Status', 'Date Joined']]
        
        for patient in patients[:50]:  # Limit to first 50 patients for PDF
            patient_data.append([
                patient.get_full_name(),
                patient.email,
                'Active' if patient.is_active else 'Inactive',
                patient.date_joined.strftime('%Y-%m-%d')
            ])

        patient_table = Table(patient_data, colWidths=[150, 200, 70, 100])
        patient_table.setStyle(self._get_table_style())
        elements.append(patient_table)

        doc.build(elements)
        return response

    def _get_table_style(self):
        """Define common table style for PDF exports"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])
