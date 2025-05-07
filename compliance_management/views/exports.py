import logging
from io import BytesIO
import xlsxwriter
from datetime import timedelta
import csv

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.db.models import Count, Avg, Q
from django.contrib import messages
from django.shortcuts import redirect
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from access_control.permissions import PermissionManager
from compliance_management.models import (
    ComplianceSchedule, ComplianceIssue, ComplianceMetric,
    ComplianceReminder, ComplianceAlert, PatientGroup
)

logger = logging.getLogger(__name__)

class ComplianceDashboardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'compliance_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_dashboard_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            elif export_format == 'csv':
                return self.export_csv(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"Compliance Dashboard export error: {str(e)}")
            messages.error(request, "Failed to export dashboard data")
            return redirect('compliance_management:compliance_dashboard')

    def gather_dashboard_data(self):
        """Gather all compliance dashboard metrics"""
        today = timezone.now()

        return {
            'summary': {
                'active_schedules': ComplianceSchedule.objects.filter(
                    status='SCHEDULED'
                ).count(),
                'open_issues': ComplianceIssue.objects.filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).count(),
                'pending_reminders': ComplianceReminder.objects.filter(
                    status='PENDING'
                ).count(),
                'active_alerts': ComplianceAlert.objects.filter(
                    is_resolved=False
                ).count()
            },
            'compliance_metrics': {
                'medication': ComplianceMetric.objects.filter(
                    metric_type='MEDICATION'
                ).aggregate(avg=Avg('compliance_score'))['avg'] or 0,
                'appointment': ComplianceMetric.objects.filter(
                    metric_type='APPOINTMENT'
                ).aggregate(avg=Avg('compliance_score'))['avg'] or 0,
                'overall': ComplianceMetric.objects.filter(
                    metric_type='OVERALL'
                ).aggregate(avg=Avg('compliance_score'))['avg'] or 0
            },
            'alerts_distribution': ComplianceAlert.objects.filter(
                is_resolved=False
            ).values('alert_type', 'severity').annotate(
                count=Count('id')
            ),
            'schedule_summary': ComplianceSchedule.objects.filter(
                scheduled_date=today.date()
            ).values('status').annotate(
                count=Count('id')
            ),
            'export_date': today
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
        
        # Summary Sheet
        summary_sheet = workbook.add_worksheet('Compliance Summary')
        summary_data = [
            ['Metric', 'Value'],
            ['Active Schedules', data['summary']['active_schedules']],
            ['Open Issues', data['summary']['open_issues']],
            ['Pending Reminders', data['summary']['pending_reminders']],
            ['Active Alerts', data['summary']['active_alerts']]
        ]
        self._write_sheet(summary_sheet, summary_data, header_format, cell_format)

        # Compliance Metrics Sheet
        metrics_sheet = workbook.add_worksheet('Compliance Metrics')
        metrics_data = [
            ['Metric Type', 'Score (%)'],
            ['Medication Compliance', round(data['compliance_metrics']['medication'], 2)],
            ['Appointment Compliance', round(data['compliance_metrics']['appointment'], 2)],
            ['Overall Compliance', round(data['compliance_metrics']['overall'], 2)]
        ]
        self._write_sheet(metrics_sheet, metrics_data, header_format, cell_format)

        # Alerts Distribution Sheet
        alerts_sheet = workbook.add_worksheet('Alerts Distribution')
        alerts_data = [['Alert Type', 'Severity', 'Count']]
        for alert in data['alerts_distribution']:
            alerts_data.append([
                alert['alert_type'],
                alert['severity'],
                alert['count']
            ])
        self._write_sheet(alerts_sheet, alerts_data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=compliance_dashboard_{timezone.now().strftime("%Y%m%d")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=compliance_dashboard_{timezone.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Compliance Management Dashboard Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Active Schedules', str(data['summary']['active_schedules'])],
            ['Open Issues', str(data['summary']['open_issues'])],
            ['Pending Reminders', str(data['summary']['pending_reminders'])],
            ['Active Alerts', str(data['summary']['active_alerts'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self._get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Compliance Metrics
        elements.append(Paragraph('Compliance Metrics', styles['Heading2']))
        metrics_data = [
            ['Metric Type', 'Score (%)'],
            ['Medication Compliance', f"{data['compliance_metrics']['medication']:.2f}"],
            ['Appointment Compliance', f"{data['compliance_metrics']['appointment']:.2f}"],
            ['Overall Compliance', f"{data['compliance_metrics']['overall']:.2f}"]
        ]
        metrics_table = Table(metrics_data, colWidths=[200, 100])
        metrics_table.setStyle(self._get_table_style())
        elements.append(metrics_table)

        doc.build(elements)
        return response

    def export_csv(self, data):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=compliance_dashboard_{timezone.now().strftime("%Y%m%d")}.csv'

        writer = csv.writer(response)
        
        # Write Summary Statistics
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Active Schedules', data['summary']['active_schedules']])
        writer.writerow(['Open Issues', data['summary']['open_issues']])
        writer.writerow(['Pending Reminders', data['summary']['pending_reminders']])
        writer.writerow(['Active Alerts', data['summary']['active_alerts']])
        writer.writerow([])  # Empty row for spacing

        # Write Compliance Metrics
        writer.writerow(['Compliance Metrics'])
        writer.writerow(['Metric Type', 'Score (%)'])
        writer.writerow(['Medication Compliance', f"{data['compliance_metrics']['medication']:.2f}"])
        writer.writerow(['Appointment Compliance', f"{data['compliance_metrics']['appointment']:.2f}"])
        writer.writerow(['Overall Compliance', f"{data['compliance_metrics']['overall']:.2f}"])
        writer.writerow([])  # Empty row for spacing

        # Write Alert Distribution
        writer.writerow(['Alert Distribution'])
        writer.writerow(['Alert Type', 'Severity', 'Count'])
        for alert in data['alerts_distribution']:
            writer.writerow([
                alert['alert_type'],
                alert['severity'],
                alert['count']
            ])
        writer.writerow([])  # Empty row for spacing

        # Write Schedule Summary
        writer.writerow(['Schedule Summary'])
        writer.writerow(['Status', 'Count'])
        for schedule in data['schedule_summary']:
            writer.writerow([
                schedule['status'],
                schedule['count']
            ])

        return response

    def _write_sheet(self, sheet, data, header_format, cell_format):
        for row_num, row_data in enumerate(data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)
        sheet.set_column(0, len(data[0])-1, 15)

    def _get_table_style(self):
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
        ])
