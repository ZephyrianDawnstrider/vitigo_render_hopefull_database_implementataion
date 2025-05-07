import logging
from io import BytesIO
import xlsxwriter
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.db.models import Count, Sum, Q
from django.contrib import messages
from django.shortcuts import redirect
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from access_control.permissions import PermissionManager
from asset_management.models import Asset, AssetCategory, MaintenanceSchedule, AssetAudit, InsurancePolicy

logger = logging.getLogger(__name__)

class AssetDashboardExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

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
            logger.error(f"Asset Dashboard export error: {str(e)}")
            messages.error(request, "Failed to export dashboard data")
            return redirect('asset_dashboard')

    def gather_dashboard_data(self):
        """Gather all asset dashboard metrics"""
        today = timezone.now().date()
        thirty_days = today + timezone.timedelta(days=30)

        return {
            'summary': {
                'total_assets': Asset.objects.filter(is_active=True).count(),
                'assets_in_use': Asset.objects.filter(status='IN_USE').count(),
                'maintenance_due': MaintenanceSchedule.objects.filter(
                    status='SCHEDULED',
                    scheduled_date__lte=thirty_days
                ).count(),
                'pending_audits': AssetAudit.objects.filter(
                    status__in=['PLANNED', 'IN_PROGRESS']
                ).count(),
                'expiring_insurance': InsurancePolicy.objects.filter(
                    status='ACTIVE',
                    end_date__lte=thirty_days
                ).count()
            },
            'status_distribution': Asset.objects.filter(
                is_active=True
            ).values('status').annotate(
                count=Count('id')
            ),
            'category_distribution': AssetCategory.objects.annotate(
                asset_count=Count('assets')
            ).values('name', 'asset_count'),
            'maintenance_stats': {
                'scheduled': MaintenanceSchedule.objects.filter(status='SCHEDULED').count(),
                'in_progress': MaintenanceSchedule.objects.filter(status='IN_PROGRESS').count(),
                'completed': MaintenanceSchedule.objects.filter(status='COMPLETED').count(),
                'overdue': MaintenanceSchedule.objects.filter(status='OVERDUE').count()
            },
            'recent_assets': Asset.objects.filter(
                is_active=True
            ).order_by('-created_at')[:10],
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
            ['Total Assets', data['summary']['total_assets']],
            ['Assets In Use', data['summary']['assets_in_use']],
            ['Maintenance Due', data['summary']['maintenance_due']],
            ['Pending Audits', data['summary']['pending_audits']],
            ['Expiring Insurance', data['summary']['expiring_insurance']]
        ]
        self._write_sheet(summary_sheet, summary_data, header_format, cell_format)

        # Status Distribution Sheet
        status_sheet = workbook.add_worksheet('Status Distribution')
        status_data = [['Status', 'Count']]
        for status in data['status_distribution']:
            status_data.append([status['status'], status['count']])
        self._write_sheet(status_sheet, status_data, header_format, cell_format)

        # Category Distribution Sheet
        category_sheet = workbook.add_worksheet('Category Distribution')
        category_data = [['Category', 'Asset Count']]
        for category in data['category_distribution']:
            category_data.append([category['name'], category['asset_count']])
        self._write_sheet(category_sheet, category_data, header_format, cell_format)

        # Recent Assets Sheet
        recent_sheet = workbook.add_worksheet('Recent Assets')
        recent_data = [['Asset ID', 'Name', 'Category', 'Status', 'Location']]
        for asset in data['recent_assets']:
            recent_data.append([
                asset.asset_id,
                asset.name,
                asset.category.name,
                asset.get_status_display(),
                asset.location
            ])
        self._write_sheet(recent_sheet, recent_data, header_format, cell_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=asset_dashboard_{timezone.now().strftime("%Y%m%d")}.xlsx'
        return response

    def export_pdf(self, data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=asset_dashboard_{timezone.now().strftime("%Y%m%d")}.pdf'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph('Asset Management Dashboard Report', styles['Heading1']))
        elements.append(Paragraph(f'Generated on: {data["export_date"].strftime("%Y-%m-%d")}', styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics
        elements.append(Paragraph('Summary Statistics', styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Assets', str(data['summary']['total_assets'])],
            ['Assets In Use', str(data['summary']['assets_in_use'])],
            ['Maintenance Due', str(data['summary']['maintenance_due'])],
            ['Pending Audits', str(data['summary']['pending_audits'])],
            ['Expiring Insurance', str(data['summary']['expiring_insurance'])]
        ]
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(self._get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Status Distribution
        elements.append(Paragraph('Status Distribution', styles['Heading2']))
        status_data = [['Status', 'Count']]
        for status in data['status_distribution']:
            status_data.append([status['status'], str(status['count'])])
        status_table = Table(status_data, colWidths=[200, 100])
        status_table.setStyle(self._get_table_style())
        elements.append(status_table)

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
