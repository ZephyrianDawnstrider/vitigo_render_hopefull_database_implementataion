import logging
from io import BytesIO
import xlsxwriter
from datetime import timedelta

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
from hr_management.models import (
    Employee, Department, Leave, Training, 
    PerformanceReview, Grievance, Document
)

logger = logging.getLogger(__name__)

class HRDashboardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

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
            logger.error(f"HR Dashboard export error: {str(e)}")
            messages.error(request, "Failed to export dashboard data")
            return redirect('hr_management')

    def gather_dashboard_data(self):
        """Gather all HR dashboard metrics"""
        today = timezone.now()
        this_month = today.month
        this_year = today.year

        return {
            'summary': {
                'total_employees': Employee.objects.filter(is_active=True).count(),
                'departments': Department.objects.filter(is_active=True).count(),
                'pending_leaves': Leave.objects.filter(status='PENDING').count(),
                'active_trainings': Training.objects.filter(
                    status='IN_PROGRESS'
                ).count(),
                'open_grievances': Grievance.objects.filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).count()
            },
            'department_stats': Department.objects.annotate(
                employee_count=Count('employees')
            ).values('name', 'employee_count'),
            'leave_stats': {
                'approved': Leave.objects.filter(status='APPROVED').count(),
                'pending': Leave.objects.filter(status='PENDING').count(),
                'rejected': Leave.objects.filter(status='REJECTED').count()
            },
            'performance_stats': PerformanceReview.objects.filter(
                review_date__year=this_year,
                review_date__month=this_month
            ).aggregate(
                avg_technical=Avg('technical_skills'),
                avg_communication=Avg('communication'),
                avg_teamwork=Avg('teamwork'),
                avg_productivity=Avg('productivity'),
                avg_reliability=Avg('reliability')
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
        summary_sheet = workbook.add_worksheet('Dashboard Summary')
        summary_data = [
            ['Metric', 'Value'],
            ['Total Employees', data['summary']['total_employees']],
            ['Departments', data['summary']['departments']],
            ['Pending Leaves', data['summary']['pending_leaves']],
            ['Active Trainings', data['summary']['active_trainings']],
            ['Open Grievances', data['summary']['open_grievances']]
        ]
        self._write_sheet(summary_sheet, summary_data, header_format, cell_format)

        # Department Stats Sheet
        dept_sheet = workbook.add_worksheet('Department Statistics')
        dept_data = [['Department', 'Employee Count']]
        for dept in data['department_stats']:
            dept_data.append([dept['name'], dept['employee_count']])
        self._write_sheet(dept_sheet, dept_data, header_format, cell_format)

        # Performance Metrics Sheet
        perf_sheet = workbook.add_worksheet('Performance Metrics')
        perf_data = [
            ['Metric', 'Average Score'],
            ['Technical Skills', data['performance_stats']['avg_technical'] or 0],
            ['Communication', data['performance_stats']['avg_communication'] or 0],
            ['Teamwork', data['performance_stats']['avg_teamwork'] or 0],
            ['Productivity', data['performance_stats']['avg_productivity'] or 0],
            ['Reliability', data['performance_stats']['avg_reliability'] or 0]
        ]
        self._write_sheet(perf_sheet, perf_data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=hr_dashboard_{timezone.now().strftime("%Y%m%d")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=hr_dashboard_{timezone.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('HR Management Dashboard Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Employees', str(data['summary']['total_employees'])],
            ['Departments', str(data['summary']['departments'])],
            ['Pending Leaves', str(data['summary']['pending_leaves'])],
            ['Active Trainings', str(data['summary']['active_trainings'])],
            ['Open Grievances', str(data['summary']['open_grievances'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self._get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Department Statistics
        elements.append(Paragraph('Department Statistics', styles['Heading2']))
        dept_data = [['Department', 'Employee Count']]
        for dept in data['department_stats']:
            dept_data.append([dept['name'], str(dept['employee_count'])])
        dept_table = Table(dept_data, colWidths=[200, 100])
        dept_table.setStyle(self._get_table_style())
        elements.append(dept_table)

        doc.build(elements)
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
