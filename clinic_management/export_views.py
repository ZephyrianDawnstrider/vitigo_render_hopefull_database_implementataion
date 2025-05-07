from datetime import datetime, timedelta
import logging
from io import BytesIO
import xlsxwriter

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.db.models import Count, Q
from django.db import models
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from access_control.permissions import PermissionManager
from .models import ClinicVisit, VisitChecklist, VisitStatus, ClinicChecklist

logger = logging.getLogger(__name__)

class ClinicDashboardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'clinic_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
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

        visits = ClinicVisit.objects.all()
        checklists = VisitChecklist.objects.all()
        statuses = VisitStatus.objects.all()

        return {
            'summary': {
                'total_active_visits': visits.filter(current_status__is_terminal_state=False).count(),
                'total_checklists': ClinicChecklist.objects.filter(is_active=True).count(),
                'status_types': statuses.count(),
                'completed_today': visits.filter(
                    completion_time__date=today.date(),
                    current_status__is_terminal_state=True
                ).count(),
                'monthly_visits': visits.filter(
                    visit_date__month=current_month,
                    visit_date__year=current_year
                ).count()
            },
            'visits': visits.order_by('-visit_date')[:10],
            'checklists': checklists.order_by('-completed_at')[:10],
            'statuses': statuses,
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
        self._create_summary_sheet(workbook, data, header_format, cell_format)
        
        # Visits Sheet
        self._create_visits_sheet(workbook, data, header_format, cell_format)
        
        # Checklists Sheet
        self._create_checklists_sheet(workbook, data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=clinic_dashboard.xlsx'
        return response

    def _create_summary_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Summary')
        summary_data = [
            ['Metric', 'Value'],
            ['Active Visits', data['summary']['total_active_visits']],
            ['Active Checklists', data['summary']['total_checklists']],
            ['Status Types', data['summary']['status_types']],
            ['Completed Today', data['summary']['completed_today']],
            ['Monthly Visits', data['summary']['monthly_visits']]
        ]
        for row_num, row_data in enumerate(summary_data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)

    def _create_visits_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Recent Visits')
        headers = ['Visit Number', 'Patient', 'Date', 'Status', 'Priority']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, visit in enumerate(data['visits'], start=1):
            sheet.write(row, 0, visit.visit_number, cell_format)
            sheet.write(row, 1, visit.patient.get_full_name(), cell_format)
            sheet.write(row, 2, visit.visit_date.strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 3, visit.current_status.display_name, cell_format)
            sheet.write(row, 4, dict(visit.PRIORITY_CHOICES)[visit.priority], cell_format)

    def _create_checklists_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Recent Checklists')
        headers = ['Visit', 'Checklist', 'Completed By', 'Completed At']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, checklist in enumerate(data['checklists'], start=1):
            sheet.write(row, 0, checklist.visit.visit_number, cell_format)
            sheet.write(row, 1, checklist.checklist.name, cell_format)
            sheet.write(row, 2, checklist.completed_by.get_full_name() if checklist.completed_by else 'N/A', cell_format)
            sheet.write(row, 3, checklist.completed_at.strftime('%Y-%m-%d %H:%M'), cell_format)

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=clinic_dashboard.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Clinic Management Dashboard Report', styles['Heading1']))
        elements.append(Spacer(1, 20))

        # Summary Table
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Active Visits', str(data['summary']['total_active_visits'])],
            ['Active Checklists', str(data['summary']['total_checklists'])],
            ['Status Types', str(data['summary']['status_types'])],
            ['Completed Today', str(data['summary']['completed_today'])],
            ['Monthly Visits', str(data['summary']['monthly_visits'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

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
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])

class VisitDataExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'clinic_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            visits = ClinicVisit.objects.select_related(
                'patient', 'current_status', 'created_by'
            ).prefetch_related(
                'checklists', 'status_logs'
            ).order_by('-visit_date')

            if date_from:
                visits = visits.filter(visit_date__gte=date_from)
            if date_to:
                visits = visits.filter(visit_date__lte=date_to)

            if export_format == 'pdf':
                return self.export_pdf(visits)
            else:
                return self.export_excel(visits)  # Default to Excel
                
        except Exception as e:
            logger.error(f"Visit data export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def export_excel(self, visits):
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
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'yyyy-mm-dd'
        })

        # Create Visits sheet
        sheet = workbook.add_worksheet('Visit Data')
        
        headers = [
            'Visit Number',
            'Patient Name',
            'Patient ID',
            'Visit Date',
            'Status',
            'Priority',
            'Registration Time',
            'Completion Time',
            'Total Duration',
            'Checklists Completed',
            'Created By',
            'Notes'
        ]

        # Set column widths
        widths = [15, 30, 15, 15, 20, 15, 20, 20, 15, 15, 25, 40]
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Write data
        for row, visit in enumerate(visits, start=1):
            completion_time = visit.completion_time.strftime('%Y-%m-%d %H:%M') if visit.completion_time else 'N/A'
            duration = (visit.completion_time - visit.registration_time).total_seconds()/3600 if visit.completion_time else 'N/A'
            checklists_completed = visit.checklists.filter(completed_at__isnull=False).count()

            data = [
                visit.visit_number,
                visit.patient.get_full_name(),
                visit.patient.id,
                visit.visit_date,
                visit.current_status.display_name,
                dict(visit.PRIORITY_CHOICES)[visit.priority],
                visit.registration_time.strftime('%Y-%m-%d %H:%M'),
                completion_time,
                f"{duration:.2f} hrs" if isinstance(duration, float) else duration,
                checklists_completed,
                visit.created_by.get_full_name() if visit.created_by else 'System',
                visit.notes or ''
            ]

            for col, value in enumerate(data):
                if col == 3:  # Visit Date column
                    sheet.write(row, col, value, date_format)
                else:
                    sheet.write(row, col, value, cell_format)

        workbook.close()
        output.seek(0)

        filename = f'visit_data_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    def export_pdf(self, visits):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=visit_data_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Visit Data Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Total Visits', str(visits.count())],
            ['Active Visits', str(visits.filter(current_status__is_terminal_state=False).count())],
            ['Completed Visits', str(visits.filter(current_status__is_terminal_state=True).count())]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Visits Table
        elements.append(Paragraph('Visit Details', styles['Heading2']))
        visit_data = [['Visit Number', 'Patient', 'Date', 'Status', 'Priority']]
        
        for visit in visits[:50]:  # Limit to 50 most recent visits for PDF
            visit_data.append([
                visit.visit_number,
                visit.patient.get_full_name(),
                visit.visit_date.strftime('%Y-%m-%d'),
                visit.current_status.display_name,
                dict(visit.PRIORITY_CHOICES)[visit.priority]
            ])

        visit_table = Table(visit_data, colWidths=[100, 150, 100, 120, 80])
        visit_table.setStyle(self.get_table_style())
        elements.append(visit_table)

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

class ChecklistDataExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'clinic_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_checklist_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"Checklist export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def gather_checklist_data(self):
        checklists = ClinicChecklist.objects.prefetch_related(
            'items', 
            'visitchecklist_set__visit',
            'visitchecklist_set__completed_by'
        ).annotate(
            total_uses=Count('visitchecklist'),
            completion_rate=Count('visitchecklist', 
                filter=Q(visitchecklist__completed_at__isnull=False)) * 100.0 / 
                    Count('visitchecklist', output_field=models.FloatField())
        )

        return {
            'checklists': checklists,
            'total_checklists': checklists.count(),
            'active_checklists': checklists.filter(is_active=True).count(),
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
        percent_format = workbook.add_format({
            'border': 1,
            'num_format': '0.00%'
        })

        # Create Overview sheet
        self._create_overview_sheet(workbook, data, header_format, cell_format, percent_format)
        
        # Create Items sheet
        self._create_items_sheet(workbook, data, header_format, cell_format)
        
        # Create Usage sheet
        self._create_usage_sheet(workbook, data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=checklist_report.xlsx'
        return response

    def _create_overview_sheet(self, workbook, data, header_format, cell_format, percent_format):
        sheet = workbook.add_worksheet('Overview')
        headers = ['Checklist Name', 'Items Count', 'Total Uses', 'Completion Rate', 'Status']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 15 if col != 0 else 30)
            
        for row, checklist in enumerate(data['checklists'], start=1):
            sheet.write(row, 0, checklist.name, cell_format)
            sheet.write(row, 1, checklist.items.count(), cell_format)
            sheet.write(row, 2, checklist.total_uses, cell_format)
            sheet.write(row, 3, checklist.completion_rate/100 if checklist.completion_rate else 0, percent_format)
            sheet.write(row, 4, 'Active' if checklist.is_active else 'Inactive', cell_format)

    def _create_items_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Checklist Items')
        headers = ['Checklist', 'Item', 'Required', 'Order', 'Help Text']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20 if col != 4 else 40)
            
        row = 1
        for checklist in data['checklists']:
            for item in checklist.items.all():
                sheet.write(row, 0, checklist.name, cell_format)
                sheet.write(row, 1, item.description, cell_format)
                sheet.write(row, 2, 'Yes' if item.is_required else 'No', cell_format)
                sheet.write(row, 3, item.order, cell_format)
                sheet.write(row, 4, item.help_text or '', cell_format)
                row += 1

    def _create_usage_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Recent Usage')
        headers = ['Date', 'Checklist', 'Visit', 'Completed By', 'Duration']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20)
            
        row = 1
        for checklist in data['checklists']:
            for usage in checklist.visitchecklist_set.all()[:20]:  # Last 20 uses
                if usage.completed_at:
                    duration = (usage.completed_at - usage.visit.registration_time).total_seconds() / 60
                else:
                    duration = 'N/A'
                
                sheet.write(row, 0, usage.completed_at.strftime('%Y-%m-%d %H:%M') if usage.completed_at else 'Pending', cell_format)
                sheet.write(row, 1, checklist.name, cell_format)
                sheet.write(row, 2, usage.visit.visit_number, cell_format)
                sheet.write(row, 3, usage.completed_by.get_full_name() if usage.completed_by else 'N/A', cell_format)
                sheet.write(row, 4, f"{duration:.0f} min" if isinstance(duration, float) else duration, cell_format)
                row += 1

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=checklist_report.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Clinic Checklist Report', styles['Heading1']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary', styles['Heading2']))
        summary_data = [
            ['Total Checklists', str(data['total_checklists'])],
            ['Active Checklists', str(data['active_checklists'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Checklists Overview
        elements.append(Paragraph('Checklists Overview', styles['Heading2']))
        overview_data = [['Checklist Name', 'Items', 'Uses', 'Status']]
        for checklist in data['checklists']:
            overview_data.append([
                checklist.name,
                str(checklist.items.count()),
                str(checklist.total_uses),
                'Active' if checklist.is_active else 'Inactive'
            ])
        overview_table = Table(overview_data, colWidths=[200, 100, 100, 100])
        overview_table.setStyle(self.get_table_style())
        elements.append(overview_table)

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

class AnalyticsExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'clinic_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'excel')
            data = self.gather_analytics_data()
            
            if export_format == 'excel':
                return self.export_excel(data)
            elif export_format == 'pdf':
                return self.export_pdf(data)
            else:
                return HttpResponse('Invalid format specified', status=400)
        except Exception as e:
            logger.error(f"Analytics export error: {str(e)}")
            return HttpResponse('Export failed', status=500)

    def gather_analytics_data(self):
        today = timezone.now()
        thirty_days_ago = today - timedelta(days=30)

        visits = ClinicVisit.objects.filter(visit_date__gte=thirty_days_ago)
        statuses = VisitStatus.objects.all()

        status_counts = {
            status.display_name: visits.filter(current_status=status).count()
            for status in statuses
        }

        monthly_trend = (
            visits.values('visit_date')
            .annotate(count=Count('id'))
            .order_by('visit_date')
        )

        checklist_completion = (
            VisitChecklist.objects
            .values('checklist__name')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(completed_at__isnull=False))
            )
        )

        priority_distribution = (
            visits.values('priority')
            .annotate(count=Count('id'))
            .order_by('priority')
        )

        return {
            'summary': {
                'total_visits': visits.count(),
                'avg_daily_visits': visits.count() / 30,
                'completion_rate': (
                    visits.filter(current_status__is_terminal_state=True).count() /
                    visits.count() * 100 if visits.count() > 0 else 0
                )
            },
            'status_distribution': status_counts,
            'monthly_trend': monthly_trend,
            'checklist_stats': checklist_completion,
            'priority_distribution': {
                priority['priority']: priority['count']
                for priority in priority_distribution
            },
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
        percent_format = workbook.add_format({
            'border': 1,
            'num_format': '0.00%'
        })

        # Create sheets
        self._create_summary_sheet(workbook, data, header_format, cell_format, percent_format)
        self._create_status_sheet(workbook, data, header_format, cell_format)
        self._create_trend_sheet(workbook, data, header_format, cell_format)
        self._create_checklist_sheet(workbook, data, header_format, cell_format, percent_format)

        workbook.close()
        output.seek(0)

        filename = f'clinic_analytics_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    def _create_summary_sheet(self, workbook, data, header_format, cell_format, percent_format):
        sheet = workbook.add_worksheet('Summary')
        summary_data = [
            ['Metric', 'Value'],
            ['Total Visits (30 days)', data['summary']['total_visits']],
            ['Average Daily Visits', f"{data['summary']['avg_daily_visits']:.2f}"],
            ['Completion Rate', data['summary']['completion_rate'] / 100],
        ]
        
        for row_num, row_data in enumerate(summary_data):
            for col_num, cell_value in enumerate(row_data):
                if row_num == 0:
                    sheet.write(row_num, col_num, cell_value, header_format)
                elif col_num == 1 and isinstance(cell_value, float) and row_num == 3:
                    sheet.write(row_num, col_num, cell_value, percent_format)
                else:
                    sheet.write(row_num, col_num, cell_value, cell_format)

    def _create_status_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Status Distribution')
        headers = ['Status', 'Count', 'Percentage']
        
        total = sum(data['status_distribution'].values())
        
        status_data = [[status, count, count/total] 
                      for status, count in data['status_distribution'].items()]
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, (status, count, percentage) in enumerate(status_data, start=1):
            sheet.write(row, 0, status, cell_format)
            sheet.write(row, 1, count, cell_format)
            sheet.write(row, 2, percentage, cell_format)

    def _create_trend_sheet(self, workbook, data, header_format, cell_format):
        sheet = workbook.add_worksheet('Visit Trends')
        headers = ['Date', 'Visit Count']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, trend in enumerate(data['monthly_trend'], start=1):
            sheet.write(row, 0, trend['visit_date'].strftime('%Y-%m-%d'), cell_format)
            sheet.write(row, 1, trend['count'], cell_format)

    def _create_checklist_sheet(self, workbook, data, header_format, cell_format, percent_format):
        sheet = workbook.add_worksheet('Checklist Stats')
        headers = ['Checklist', 'Total', 'Completed', 'Completion Rate']
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            
        for row, stat in enumerate(data['checklist_stats'], start=1):
            completion_rate = stat['completed'] / stat['total'] if stat['total'] > 0 else 0
            sheet.write(row, 0, stat['checklist__name'], cell_format)
            sheet.write(row, 1, stat['total'], cell_format)
            sheet.write(row, 2, stat['completed'], cell_format)
            sheet.write(row, 3, completion_rate, percent_format)

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=clinic_analytics_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Clinic Analytics Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Section
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Visits (30 days)', str(data['summary']['total_visits'])],
            ['Average Daily Visits', f"{data['summary']['avg_daily_visits']:.2f}"],
            ['Completion Rate', f"{data['summary']['completion_rate']:.2f}%"]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self.get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Status Distribution
        elements.append(Paragraph('Status Distribution', styles['Heading2']))
        status_data = [['Status', 'Count']]
        status_data.extend([
            [status, count] for status, count in data['status_distribution'].items()
        ])
        status_table = Table(status_data, colWidths=[200, 100])
        status_table.setStyle(self.get_table_style())
        elements.append(status_table)

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
