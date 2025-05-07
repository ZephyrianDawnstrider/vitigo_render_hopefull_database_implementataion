from datetime import datetime
import logging
from io import BytesIO
import xlsxwriter
import csv

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.db.models import Count, Avg, Sum, Q
from django.db import models
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.contrib import messages
from django.shortcuts import redirect
from datetime import timedelta

from access_control.permissions import PermissionManager
from phototherapy_management.models import (
    PhototherapyPlan, PhototherapySession, PhototherapyDevice,
    PhototherapyType, PhototherapyPayment, PhototherapyProgress, PhototherapyProtocol, ProblemReport, DeviceMaintenance, PatientRFIDCard
)

logger = logging.getLogger(__name__)

class PhototherapyDashboardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            
            # Collect all necessary data
            data = self.gather_dashboard_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def gather_dashboard_data(self):
        """Gather all dashboard metrics and data"""
        today = timezone.now()
        current_month = today.month
        current_year = today.year

        plans = PhototherapyPlan.objects.all()
        sessions = PhototherapySession.objects.all()
        devices = PhototherapyDevice.objects.all()
        payments = PhototherapyPayment.objects.filter(status='COMPLETED')

        return {
            'summary': {
                'total_active_plans': plans.filter(is_active=True).count(),
                'total_completed_sessions': sessions.filter(status='COMPLETED').count(),
                'total_missed_sessions': sessions.filter(status='MISSED').count(),
                'active_devices': devices.filter(is_active=True).count(),
                'maintenance_needed': devices.filter(
                    next_maintenance_date__lte=today.date()
                ).count(),
                'monthly_sessions': sessions.filter(
                    scheduled_date__month=current_month,
                    scheduled_date__year=current_year
                ).count(),
                'monthly_revenue': payments.filter(
                    payment_date__month=current_month,
                    payment_date__year=current_year
                ).count()
            },
            'therapy_types': PhototherapyType.objects.all(),
            'recent_sessions': sessions.order_by('-scheduled_date')[:10],
            'recent_payments': payments.order_by('-payment_date')[:10],
            'progress_stats': PhototherapyProgress.objects.all()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Styles
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        
        # Summary Sheet
        summary_sheet = workbook.add_worksheet('Dashboard Summary')
        summary_data = [
            ['Metric', 'Value'],
            ['Active Treatment Plans', data['summary']['total_active_plans']],
            ['Completed Sessions', data['summary']['total_completed_sessions']],
            ['Missed Sessions', data['summary']['total_missed_sessions']],
            ['Active Devices', data['summary']['active_devices']],
            ['Devices Needing Maintenance', data['summary']['maintenance_needed']],
            ['Sessions This Month', data['summary']['monthly_sessions']],
            ['Monthly Revenue', data['summary']['monthly_revenue']]
        ]
        self.write_sheet_data(summary_sheet, summary_data, header_format, cell_format)

        # Recent Sessions Sheet
        sessions_sheet = workbook.add_worksheet('Recent Sessions')
        sessions_data = [['Date', 'Patient', 'Type', 'Status', 'Duration']]
        for session in data['recent_sessions']:
            sessions_data.append([
                session.scheduled_date.strftime('%Y-%m-%d'),
                session.plan.patient.get_full_name(),
                session.plan.protocol.phototherapy_type.name,
                session.get_status_display(),
                f"{session.duration_seconds/60:.0f} min" if session.duration_seconds else 'N/A'
            ])
        self.write_sheet_data(sessions_sheet, sessions_data, header_format, cell_format)

        # Recent Payments Sheet
        payments_sheet = workbook.add_worksheet('Recent Payments')
        payments_data = [['Date', 'Amount', 'Method', 'Status']]
        for payment in data['recent_payments']:
            payments_data.append([
                payment.payment_date.strftime('%Y-%m-%d'),
                f"${payment.amount}",
                payment.get_payment_method_display(),
                payment.get_status_display()
            ])
        self.write_sheet_data(payments_sheet, payments_data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=phototherapy_dashboard.xlsx'
        return response

    def write_sheet_data(self, sheet, data, header_format, cell_format):
        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)
        sheet.set_column(0, len(data[0])-1, 15)  # Set column width

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=phototherapy_dashboard.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']

        # Title
        elements.append(Paragraph('Phototherapy Dashboard Report', title_style))
        elements.append(Paragraph(f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary Statistics', subtitle_style))
        summary_data = [
            ['Metric', 'Value'],
            ['Active Treatment Plans', str(data['summary']['total_active_plans'])],
            ['Completed Sessions', str(data['summary']['total_completed_sessions'])],
            ['Missed Sessions', str(data['summary']['total_missed_sessions'])],
            ['Active Devices', str(data['summary']['active_devices'])],
            ['Devices Needing Maintenance', str(data['summary']['maintenance_needed'])],
            ['Sessions This Month', str(data['summary']['monthly_sessions'])],
            ['Monthly Revenue', f"${data['summary']['monthly_revenue']}"]
        ]
        summary_table = Table(summary_data, colWidths=[300, 200])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Recent Sessions
        elements.append(Paragraph('Recent Sessions', subtitle_style))
        sessions_data = [['Date', 'Patient', 'Type', 'Status']]
        for session in data['recent_sessions']:
            sessions_data.append([
                session.scheduled_date.strftime('%Y-%m-%d'),
                session.plan.patient.get_full_name(),
                session.plan.protocol.phototherapy_type.name,
                session.get_status_display()
            ])
        sessions_table = Table(sessions_data, colWidths=[100, 200, 150, 100])
        sessions_table.setStyle(self.get_table_style())
        elements.append(sessions_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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

class ProtocolExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_protocol_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"Protocol export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def gather_protocol_data(self):
        """Gather all protocol related data"""
        protocols = PhototherapyProtocol.objects.select_related(
            'phototherapy_type', 'created_by'
        ).annotate(
            active_plans=Count('phototherapyplan'),
            avg_improvement=Avg('phototherapyplan__progress_records__improvement_percentage')
        )

        return {
            'protocols': protocols,
            'total_protocols': protocols.count(),
            'active_protocols': protocols.filter(is_active=True).count(),
            'export_date': timezone.now()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '0.00'  # Format for decimal numbers
        })

        # Create Protocols sheet
        sheet = workbook.add_worksheet('Protocols')
        
        # Define headers with split dose range
        headers = [
            'Protocol Name',
            'Type',
            'Initial Dose (mJ/cm²)',
            'Max Dose (mJ/cm²)',
            'Increment %',
            'Duration (weeks)',
            'Frequency/week',
            'Active Plans',
            'Avg Improvement',
            'Status',
            'Created By',
            'Created Date'
        ]

        # Set column widths
        column_widths = {
            0: 25,  # Protocol Name
            1: 15,  # Type
            2: 18,  # Initial Dose
            3: 18,  # Max Dose
            4: 12,  # Increment
            5: 15,  # Duration
            6: 13,  # Frequency
            7: 12,  # Active Plans
            8: 15,  # Avg Improvement
            9: 10,  # Status
            10: 20, # Created By
            11: 12  # Created Date
        }
        
        for col, width in column_widths.items():
            sheet.set_column(col, col, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data with split dose columns
        for row, protocol in enumerate(data['protocols'], start=1):
            sheet.write(row, 0, protocol.name, cell_format)
            sheet.write(row, 1, protocol.phototherapy_type.name, cell_format)
            sheet.write(row, 2, protocol.initial_dose, number_format)
            sheet.write(row, 3, protocol.max_dose, number_format)
            sheet.write(row, 4, protocol.increment_percentage, number_format)
            sheet.write(row, 5, protocol.duration_weeks, cell_format)
            sheet.write(row, 6, protocol.frequency_per_week, cell_format)
            sheet.write(row, 7, protocol.active_plans, cell_format)
            sheet.write(row, 8, protocol.avg_improvement or 0, number_format)
            sheet.write(row, 9, 'Active' if protocol.is_active else 'Inactive', cell_format)
            sheet.write(row, 10, protocol.created_by.get_full_name(), cell_format)
            sheet.write(row, 11, protocol.created_at.strftime('%Y-%m-%d'), cell_format)

        workbook.close()
        
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=protocols_export.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=protocols_export.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Phototherapy Protocols Report', styles['Heading1']))
        elements.append(Paragraph(
            f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}',
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        # Summary
        elements.append(Paragraph('Summary', styles['Heading2']))
        summary_data = [
            ['Total Protocols', str(data['total_protocols'])],
            ['Active Protocols', str(data['active_protocols'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Protocols table with split dose columns
        elements.append(Paragraph('Protocol Details', styles['Heading2']))
        protocol_data = [
            ['Name', 'Type', 'Initial Dose', 'Max Dose', 'Duration', 'Status']
        ]
        
        for protocol in data['protocols']:
            protocol_data.append([
                protocol.name,
                protocol.phototherapy_type.name,
                f"{protocol.initial_dose:.2f}",
                f"{protocol.max_dose:.2f}",
                f"{protocol.duration_weeks} weeks",
                'Active' if protocol.is_active else 'Inactive'
            ])

        # Adjust column widths for better readability
        protocol_table = Table(protocol_data, colWidths=[100, 80, 70, 70, 70, 60])
        protocol_table.setStyle(self.get_table_style())
        elements.append(protocol_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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

class HomeTherapyLogsExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('export', 'excel')
            data = self.gather_logs_data(request)
            
            # Explicitly check the format
            if export_format == 'pdf':
                return self.export_pdf(data)
            else:  # default to excel
                return self.export_excel(data)
        except Exception as e:
            logger.error(f"Home therapy logs export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def gather_logs_data(self, request):
        """Gather all home therapy logs data with filters"""
        from .home import HomeTherapyLogsView
        
        # Reuse the filtering logic from HomeTherapyLogsView
        view = HomeTherapyLogsView()
        view.request = request
        queryset = view.get_queryset()

        return {
            'logs': queryset.select_related('plan__patient'),
            'total_logs': queryset.count(),
            'total_duration': queryset.aggregate(total=Sum('duration_minutes'))['total'] or 0,
            'unique_patients': queryset.values('plan__patient').distinct().count(),
            'export_date': timezone.now()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})

        # Create sheet
        sheet = workbook.add_worksheet('Home Therapy Logs')

        # Define headers
        headers = [
            'Patient Name',
            'Date',
            'Time',
            'Duration (mins)',
            'Exposure Type',
            'Body Areas',
            'Notes',
            'Side Effects'
        ]

        # Set column widths
        widths = [25, 15, 15, 15, 20, 30, 30, 30]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, log in enumerate(data['logs'], start=1):
            sheet.write(row, 0, log.plan.patient.get_full_name(), cell_format)
            sheet.write(row, 1, log.date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 2, log.time.strftime('%H:%M'), cell_format)
            sheet.write(row, 3, log.duration_minutes, cell_format)
            sheet.write(row, 4, log.get_exposure_type_display(), cell_format)
            sheet.write(row, 5, log.body_areas_treated, cell_format)
            sheet.write(row, 6, log.notes or '', cell_format)
            sheet.write(row, 7, log.side_effects or '', cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=home_therapy_logs.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=home_therapy_logs.pdf'

        # Use landscape mode with letter size for more width
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Add custom style for wrapped text
        styles.add(ParagraphStyle(
            name='WrappedText',
            parent=styles['Normal'],
            fontSize=9,
            wordWrap='CJK',
            alignment=1  # Center alignment
        ))

        # Title and date
        elements.append(Paragraph('Home Therapy Logs Report', styles['Heading1']))
        elements.append(Paragraph(
            f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}',
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        # Summary section remains the same
        elements.append(Paragraph('Summary', styles['Heading2']))
        summary_data = [
            ['Total Logs', str(data['total_logs'])],
            ['Total Duration', f"{data['total_duration']} minutes"],
            ['Unique Patients', str(data['unique_patients'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Logs table with adjusted column widths and wrapped text
        elements.append(Paragraph('Log Details', styles['Heading2']))
        logs_data = [
            ['Patient', 'Date', 'Duration', 'Exposure Type', 'Body Areas']
        ]
        
        # Process the data with wrapped text for body areas
        for log in data['logs']:
            logs_data.append([
                log.plan.patient.get_full_name(),
                log.date.strftime('%Y-%m-%d'),
                f"{log.duration_minutes} mins",
                log.get_exposure_type_display(),
                Paragraph(log.body_areas_treated, styles['WrappedText'])
            ])

        # Adjusted column widths (total should be around 700-750 for landscape letter)
        logs_table = Table(logs_data, colWidths=[150, 80, 80, 100, 250])
        
        # Enhanced table style for better readability
        table_style = self.get_table_style()
        table_style.add('VALIGN', (0, 0), (-1, -1), 'MIDDLE')  # Vertical alignment
        table_style.add('ROWHEIGHT', (0, 1), (-1, -1), 30)     # Minimum row height
        
        logs_table.setStyle(table_style)
        elements.append(logs_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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

class DeviceDataExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_device_data()
            
            if export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return self.export_excel(data)  # Default to Excel
                
        except Exception as e:
            logger.error(f"Device data export error: {str(e)}")
            messages.error(request, "Failed to export device data")
            return redirect('device_management')

    def gather_device_data(self):
        """Gather all device-related data for export"""
        devices = PhototherapyDevice.objects.select_related(
            'phototherapy_type'
        ).prefetch_related(
            'maintenance_records'
        ).order_by('name')

        return {
            'devices': devices,
            'total_devices': devices.count(),
            'active_devices': devices.filter(is_active=True).count(),
            'maintenance_needed': devices.filter(
                next_maintenance_date__lte=timezone.now().date()
            ).count(),
            'export_date': timezone.now()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})

        # Create Devices sheet
        sheet = workbook.add_worksheet('Devices')
        
        headers = [
            'Device Name',
            'Model Number',
            'Serial Number',
            'Type',
            'Location',
            'Status',
            'Installation Date',
            'Last Maintenance',
            'Next Maintenance',
            'Maintenance Notes'
        ]

        # Set column widths
        widths = [25, 20, 20, 15, 20, 10, 15, 15, 15, 40]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, device in enumerate(data['devices'], start=1):
            sheet.write(row, 0, device.name, cell_format)
            sheet.write(row, 1, device.model_number, cell_format)
            sheet.write(row, 2, device.serial_number, cell_format)
            sheet.write(row, 3, device.phototherapy_type.name, cell_format)
            sheet.write(row, 4, device.location, cell_format)
            sheet.write(row, 5, 'Active' if device.is_active else 'Inactive', cell_format)
            sheet.write(row, 6, device.installation_date, date_format)
            sheet.write(row, 7, device.last_maintenance_date or 'N/A', date_format if device.last_maintenance_date else cell_format)
            sheet.write(row, 8, device.next_maintenance_date or 'N/A', date_format if device.next_maintenance_date else cell_format)
            sheet.write(row, 9, device.maintenance_notes or '', cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=devices_export_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=devices_export_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title and summary
        elements.append(Paragraph('Device Inventory Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary statistics
        summary_data = [
            ['Total Devices', str(data['total_devices'])],
            ['Active Devices', str(data['active_devices'])],
            ['Maintenance Needed', str(data['maintenance_needed'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Devices table
        device_data = [['Device Name', 'Type', 'Location', 'Status', 'Next Maintenance']]
        for device in data['devices']:
            device_data.append([
                device.name,
                device.phototherapy_type.name,
                device.location,
                'Active' if device.is_active else 'Inactive',
                device.next_maintenance_date.strftime('%Y-%m-%d') if device.next_maintenance_date else 'N/A'
            ])

        device_table = Table(device_data, colWidths=[150, 100, 100, 80, 100])
        device_table.setStyle(self.get_table_style())
        elements.append(device_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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

class ReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            date_range = request.GET.get('days', '30')
            
            # Get the data from the report management view's logic
            data = self.gather_report_data(date_range)
            
            if export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return self.export_excel(data)
                
        except Exception as e:
            logger.error(f"Report export error: {str(e)}")
            messages.error(request, "Failed to export reports")
            return redirect('report_management')

    def gather_report_data(self, date_range):
        """Gather all report data for the specified date range"""
        today = timezone.now().date()
        start_date = today - timedelta(days=int(date_range))
        
        problem_reports = ProblemReport.objects.filter(
            reported_at__date__gte=start_date
        ).select_related('session', 'reported_by')
        
        progress_records = PhototherapyProgress.objects.filter(
            assessment_date__gte=start_date
        ).select_related('plan', 'assessed_by')
        
        maintenance_records = DeviceMaintenance.objects.filter(
            maintenance_date__gte=start_date
        ).select_related('device')
        
        sessions = PhototherapySession.objects.filter(
            scheduled_date__gte=start_date
        )

        return {
            'date_range': date_range,
            'problem_reports': problem_reports,
            'progress_records': progress_records,
            'maintenance_records': maintenance_records,
            'sessions': sessions,
            'export_date': timezone.now()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})

        # Problem Reports Sheet
        self._create_problems_sheet(workbook, data['problem_reports'], header_format, cell_format)
        
        # Progress Sheet
        self._create_progress_sheet(workbook, data['progress_records'], header_format, cell_format)
        
        # Maintenance Sheet
        self._create_maintenance_sheet(workbook, data['maintenance_records'], header_format, cell_format)
        
        # Sessions Sheet
        self._create_sessions_sheet(workbook, data['sessions'], header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=phototherapy_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
        return response

    def _create_problems_sheet(self, workbook, problems, header_format, cell_format):
        sheet = workbook.add_worksheet('Problem Reports')
        headers = ['Date', 'Patient', 'Problem', 'Severity', 'Status', 'Resolution Time']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, problem in enumerate(problems, start=1):
            sheet.write(row, 0, problem.reported_at.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, problem.session.plan.patient.get_full_name(), cell_format)
            sheet.write(row, 2, problem.problem_description, cell_format)
            sheet.write(row, 3, problem.get_severity_display(), cell_format)
            sheet.write(row, 4, 'Resolved' if problem.resolved else 'Pending', cell_format)
            resolution_time = problem.resolved_at - problem.reported_at if problem.resolved else 'N/A'
            sheet.write(row, 5, str(resolution_time), cell_format)

    def _create_progress_sheet(self, workbook, progress_records, header_format, cell_format):
        sheet = workbook.add_worksheet('Progress')
        headers = ['Date', 'Patient', 'Response Level', 'Improvement %', 'Next Assessment']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, progress in enumerate(progress_records, start=1):
            sheet.write(row, 0, progress.assessment_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, progress.plan.patient.get_full_name(), cell_format)
            sheet.write(row, 2, progress.get_response_level_display(), cell_format)
            sheet.write(row, 3, progress.improvement_percentage, cell_format)
            next_date = progress.next_assessment_date.strftime('%Y-%m-%d') if progress.next_assessment_date else 'N/A'
            sheet.write(row, 4, next_date, cell_format)

    def _create_maintenance_sheet(self, workbook, maintenance_records, header_format, cell_format):
        sheet = workbook.add_worksheet('Maintenance')
        headers = ['Date', 'Device', 'Type', 'Cost', 'Next Due', 'Performed By']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, maintenance in enumerate(maintenance_records, start=1):
            sheet.write(row, 0, maintenance.maintenance_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, maintenance.device.name, cell_format)
            sheet.write(row, 2, maintenance.get_maintenance_type_display(), cell_format)
            sheet.write(row, 3, float(maintenance.cost), cell_format)
            next_due = maintenance.next_maintenance_due.strftime('%Y-%m-%d') if maintenance.next_maintenance_due else 'N/A'
            sheet.write(row, 4, next_due, cell_format)
            sheet.write(row, 5, maintenance.performed_by, cell_format)

    def _create_sessions_sheet(self, workbook, sessions, header_format, cell_format):
        sheet = workbook.add_worksheet('Sessions')
        headers = ['Date', 'Patient', 'Device', 'Status', 'Duration', 'Dose']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, session in enumerate(sessions, start=1):
            sheet.write(row, 0, session.scheduled_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, session.plan.patient.get_full_name(), cell_format)
            sheet.write(row, 2, session.device.name if session.device else 'N/A', cell_format)
            sheet.write(row, 3, session.get_status_display(), cell_format)
            sheet.write(row, 4, session.duration_seconds or 'N/A', cell_format)
            sheet.write(row, 5, session.actual_dose or 'N/A', cell_format)

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=phototherapy_report_{timezone.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Phototherapy Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Problems Summary
        elements.append(Paragraph('Problem Reports', styles['Heading2']))
        problem_data = [['Date', 'Severity', 'Status']]
        for problem in data['problem_reports']:
            problem_data.append([
                problem.reported_at.strftime('%Y-%m-%d'),
                problem.get_severity_display(),
                'Resolved' if problem.resolved else 'Pending'
            ])
        problem_table = Table(problem_data, colWidths=[100, 100, 100])
        problem_table.setStyle(self.get_table_style())
        elements.append(problem_table)
        elements.append(Spacer(1, 20))

        # Progress Summary
        elements.append(Paragraph('Treatment Progress', styles['Heading2']))
        progress_data = [['Date', 'Response', 'Improvement']]
        for progress in data['progress_records']:
            progress_data.append([
                progress.assessment_date.strftime('%Y-%m-%d'),
                progress.get_response_level_display(),
                f"{progress.improvement_percentage}%"
            ])
        progress_table = Table(progress_data, colWidths=[100, 100, 100])
        progress_table.setStyle(self.get_table_style())
        elements.append(progress_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])

class TreatmentPlanExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_treatment_plan_data()
            
            if export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return self.export_excel(data)
                
        except Exception as e:
            logger.error(f"Treatment plan export error: {str(e)}")
            messages.error(request, "Failed to export treatment plans")
            return redirect('treatment_plan_list')

    def gather_treatment_plan_data(self):
        """Gather all treatment plan related data"""
        plans = PhototherapyPlan.objects.select_related(
            'patient',
            'protocol',
            'protocol__phototherapy_type',
            'created_by',
            'rfid_card'
        ).prefetch_related(
            'sessions',
            'progress_records',
            'payments'
        )

        return {
            'plans': plans,
            'total_plans': plans.count(),
            'active_plans': plans.filter(is_active=True).count(),
            'completed_plans': plans.filter(
                sessions_completed__gte=models.F('total_sessions_planned')
            ).count(),
            'export_date': timezone.now()
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        percent_format = workbook.add_format({'border': 1, 'num_format': '0.00%'})

        # Create Plans sheet
        sheet = workbook.add_worksheet('Treatment Plans')
        
        headers = [
            'Patient Name',
            'Patient Email',
            'Protocol',
            'Start Date',
            'Sessions Completed',
            'Total Sessions',
            'Progress (%)',
            'Total Cost',
            'Amount Paid',
            'Status',
            'RFID Card',
            'Created By',
            'Created Date'
        ]

        # Set column widths
        widths = [25, 30, 20, 15, 15, 15, 15, 15, 15, 10, 15, 25, 15]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, plan in enumerate(data['plans'], start=1):
            sheet.write(row, 0, plan.patient.get_full_name(), cell_format)
            sheet.write(row, 1, plan.patient.email, cell_format)
            sheet.write(row, 2, plan.protocol.name, cell_format)
            sheet.write(row, 3, plan.start_date, date_format)
            sheet.write(row, 4, plan.sessions_completed, cell_format)
            sheet.write(row, 5, plan.total_sessions_planned, cell_format)
            sheet.write(row, 6, plan.get_completion_percentage()/100, percent_format)
            sheet.write(row, 7, float(plan.total_cost), number_format)
            sheet.write(row, 8, float(plan.amount_paid), number_format)
            sheet.write(row, 9, 'Active' if plan.is_active else 'Inactive', cell_format)
            sheet.write(row, 10, plan.rfid_card.card_number if plan.rfid_card else 'N/A', cell_format)
            sheet.write(row, 11, plan.created_by.get_full_name(), cell_format)
            sheet.write(row, 12, plan.created_at.strftime('%Y-%m-%d'), cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=treatment_plans_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=treatment_plans_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Treatment Plans Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary statistics
        summary_data = [
            ['Total Plans', str(data['total_plans'])],
            ['Active Plans', str(data['active_plans'])],
            ['Completed Plans', str(data['completed_plans'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Plans table
        plans_data = [['Patient', 'Protocol', 'Progress', 'Cost', 'Status']]
        for plan in data['plans']:
            plans_data.append([
                plan.patient.get_full_name(),
                plan.protocol.name,
                f"{plan.get_completion_percentage()}%",
                f"₹{plan.total_cost}",
                'Active' if plan.is_active else 'Inactive'
            ])

        plans_table = Table(plans_data, colWidths=[150, 150, 100, 100, 100])
        plans_table.setStyle(self.get_table_style())
        elements.append(plans_table)

        doc.build(elements)
        return response

    def get_table_style(self):
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

class RFIDCardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'phototherapy_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_rfid_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            elif export_format == 'csv':
                return self.export_csv(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"RFID card export error: {str(e)}")
            messages.error(request, "Failed to export RFID card data")
            return redirect('rfid_dashboard')

    def gather_rfid_data(self):
        """Gather all RFID card related data"""
        now = timezone.now()
        cards = PatientRFIDCard.objects.select_related(
            'patient'
        ).annotate(
            active_plans=Count('patient__phototherapy_plans',
                filter=Q(patient__phototherapy_plans__is_active=True))
        ).order_by('-assigned_date')

        return {
            'cards': cards,
            'total_cards': cards.count(),
            'active_cards': cards.filter(is_active=True, expires_at__gt=now).count(),
            'expired_cards': cards.filter(expires_at__lte=now).count(),
            'export_date': now
        }

    def export_excel(self, data):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'fg_color': '#4B5563',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})

        # Create sheet
        sheet = workbook.add_worksheet('RFID Cards')
        
        headers = [
            'Card Number',
            'Patient Name',
            'Patient Email',
            'Status',
            'Assigned Date',
            'Expiry Date',
            'Last Used',
            'Active Plans',
            'Notes'
        ]

        # Set column widths
        widths = [20, 30, 35, 15, 15, 15, 15, 15, 40]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, card in enumerate(data['cards'], start=1):
            sheet.write(row, 0, card.card_number, cell_format)
            sheet.write(row, 1, card.patient.get_full_name(), cell_format)
            sheet.write(row, 2, card.patient.email, cell_format)
            sheet.write(row, 3, 'Active' if card.is_active else 'Inactive', cell_format)
            sheet.write(row, 4, card.assigned_date.strftime('%Y-%m-%d'), date_format)
            sheet.write(row, 5, card.expires_at.strftime('%Y-%m-%d'), date_format)
            sheet.write(row, 6, card.last_used.strftime('%Y-%m-%d') if card.last_used else 'Never', cell_format)
            sheet.write(row, 7, card.active_plans, cell_format)
            sheet.write(row, 8, card.notes or '', cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=rfid_cards_{timezone.now().strftime("%Y%m%d")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=rfid_cards_{timezone.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('RFID Cards Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary statistics
        summary_data = [
            ['Total Cards', str(data['total_cards'])],
            ['Active Cards', str(data['active_cards'])],
            ['Expired Cards', str(data['expired_cards'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Cards table
        cards_data = [['Card Number', 'Patient', 'Status', 'Expiry Date', 'Active Plans']]
        for card in data['cards']:
            cards_data.append([
                card.card_number,
                card.patient.get_full_name(),
                'Active' if card.is_active else 'Inactive',
                card.expires_at.strftime('%Y-%m-%d'),
                str(card.active_plans)
            ])

        cards_table = Table(cards_data, colWidths=[100, 150, 80, 100, 80])
        cards_table.setStyle(self.get_table_style())
        elements.append(cards_table)

        doc.build(elements)
        return response

    def export_csv(self, data):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=rfid_cards_{timezone.now().strftime("%Y%m%d")}.csv'

        writer = csv.writer(response)
        writer.writerow([
            'Card Number',
            'Patient Name',
            'Patient Email',
            'Status',
            'Assigned Date',
            'Expiry Date',
            'Last Used',
            'Active Plans',
            'Notes'
        ])

        for card in data['cards']:
            writer.writerow([
                card.card_number,
                card.patient.get_full_name(),
                card.patient.email,
                'Active' if card.is_active else 'Inactive',
                card.assigned_date.strftime('%Y-%m-%d'),
                card.expires_at.strftime('%Y-%m-%d'),
                card.last_used.strftime('%Y-%m-%d') if card.last_used else 'Never',
                card.active_plans,
                card.notes or ''
            ])

        return response

    def get_table_style(self):
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
