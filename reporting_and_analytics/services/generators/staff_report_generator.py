# Standard library imports
from datetime import datetime
import pytz

# Third-party imports
import pandas as pd

# Django imports
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

# Local application imports
from query_management.models import Query

class StaffReportGenerator:
    """Handles generation of Staff/Assignment related reports"""
    
    @staticmethod
    def generate_queries_per_staff(start_date, end_date):
        """Generates report showing distribution of queries among staff members"""
        User = get_user_model()
        
        # Get base queryset within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            assigned_to__isnull=False
        )

        # Get distribution by staff member
        staff_counts = list(queries.values(
            'assigned_to',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'assigned_to__email'
        ).annotate(
            count=Count('query_id'),
            resolved_count=Count('query_id', filter=models.Q(status='RESOLVED')),
            pending_count=Count('query_id', filter=~models.Q(status='RESOLVED'))
        ).order_by('-count'))

        # Create DataFrame
        df = pd.DataFrame(staff_counts)
        
        if not df.empty:
            # Create full name and format columns
            df['Staff Member'] = df['assigned_to__first_name'] + ' ' + df['assigned_to__last_name']
            df['Email'] = df['assigned_to__email']
            df.rename(columns={
                'count': 'Total Queries',
                'resolved_count': 'Resolved Queries',
                'pending_count': 'Pending Queries'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Staff Member',
                'Email',
                'Total Queries',
                'Resolved Queries',
                'Pending Queries'
            ]]

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066cc',
                'font_color': 'white'
            })

            # Write sheet
            df.to_excel(excel_file, sheet_name='Queries per Staff', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Queries per Staff']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                if not df.empty:
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    )
                else:
                    max_length = len(str(value))
                worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_open_queries_by_staff(start_date, end_date):
        """Generates report showing current workload analysis by staff member"""
        User = get_user_model()
        
        # Get base queryset for open queries within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            assigned_to__isnull=False
        ).exclude(status__in=['RESOLVED', 'CLOSED'])

        # Get workload distribution by staff member
        staff_workload = list(queries.values(
            'assigned_to',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'assigned_to__email'
        ).annotate(
            total_open=Count('query_id'),
            high_priority=Count('query_id', filter=Q(priority='A')),
            medium_priority=Count('query_id', filter=Q(priority='B')),
            low_priority=Count('query_id', filter=Q(priority='C')),
            waiting_response=Count('query_id', filter=Q(status='WAITING')),
            in_progress=Count('query_id', filter=Q(status='IN_PROGRESS')),
            new_queries=Count('query_id', filter=Q(status='NEW'))
        ).order_by('-total_open'))

        # Create DataFrame
        df = pd.DataFrame(staff_workload)
        
        if not df.empty:
            # Create full name and format columns
            df['Staff Member'] = df['assigned_to__first_name'] + ' ' + df['assigned_to__last_name']
            df['Email'] = df['assigned_to__email']
            
            # Select and order columns
            df = df[[
                'Staff Member',
                'Email',
                'total_open',
                'high_priority',
                'medium_priority',
                'low_priority',
                'new_queries',
                'in_progress',
                'waiting_response'
            ]]
            
            # Rename columns for better readability
            df.rename(columns={
                'total_open': 'Total Open Queries',
                'high_priority': 'High Priority',
                'medium_priority': 'Medium Priority',
                'low_priority': 'Low Priority',
                'new_queries': 'New',
                'in_progress': 'In Progress',
                'waiting_response': 'Waiting for Response'
            }, inplace=True)

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066cc',
                'font_color': 'white'
            })

            # Write sheet
            df.to_excel(excel_file, sheet_name='Open Queries by Staff', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Open Queries by Staff']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                if not df.empty:
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    )
                else:
                    max_length = len(str(value))
                worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_unassigned_queries_list(start_date, end_date):
        """Generates report showing queries that are pending assignment"""
        # Get base queryset for unassigned queries within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            assigned_to__isnull=True
        ).values(
            'query_id',
            'subject',
            'created_at',
            'source',
            'priority',
            'query_type',
            'status'
        ).order_by('-created_at')

        # Create DataFrame
        df = pd.DataFrame(list(queries))
        
        if not df.empty:
            # Map codes to their display names
            source_mapping = dict(Query.SOURCE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            status_mapping = dict(Query.STATUS_CHOICES)

            # Apply mappings and rename columns
            df['source'] = df['source'].map(source_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['status'] = df['status'].map(status_mapping)
            
            # Handle null values in query_type
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns for better readability
            df.rename(columns={
                'query_id': 'Query ID',
                'subject': 'Subject',
                'created_at': 'Created Date',
                'source': 'Source',
                'priority': 'Priority',
                'query_type': 'Query Type',
                'status': 'Status'
            }, inplace=True)

            # Reorder columns
            df = df[[
                'Query ID',
                'Subject',
                'Created Date',
                'Priority',
                'Query Type',
                'Source',
                'Status'
            ]]

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066cc',
                'font_color': 'white'
            })

            # Write sheet
            df.to_excel(excel_file, sheet_name='Unassigned Queries', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Unassigned Queries']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                if not df.empty:
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    )
                else:
                    max_length = len(str(value))
                worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_staff_performance_metrics(start_date, end_date):
        """Generates comprehensive staff performance analysis report"""
        User = get_user_model()
        
        # Get base queryset for the date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            assigned_to__isnull=False
        )

        # Get detailed performance metrics by staff member
        staff_metrics = list(queries.values(
            'assigned_to',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'assigned_to__email'
        ).annotate(
            total_queries=Count('query_id'),
            resolved_queries=Count('query_id', filter=Q(status='RESOLVED')),
            # Resolution rate
            resolution_rate=Count('query_id', filter=Q(status='RESOLVED')) * 100.0 / Count('query_id'),
            # Average response time for resolved queries
            avg_response_time=models.Avg('response_time', filter=Q(status='RESOLVED')),
            # High priority handling
            high_priority_total=Count('query_id', filter=Q(priority='A')),
            high_priority_resolved=Count('query_id', filter=Q(priority='A', status='RESOLVED')),
            # Satisfaction metrics
            avg_satisfaction=models.Avg('satisfaction_rating', filter=Q(satisfaction_rating__isnull=False)),
            rated_queries=Count('query_id', filter=Q(satisfaction_rating__isnull=False)),
            # Conversion metrics
            conversion_count=Count('query_id', filter=Q(conversion_status=True)),
            convertible_queries=Count('query_id', filter=Q(conversion_status__isnull=False))
        ).order_by('-total_queries'))

        # Create DataFrame
        df = pd.DataFrame(staff_metrics)
        
        if not df.empty:
            # Create full name and format columns
            df['Staff Member'] = df['assigned_to__first_name'] + ' ' + df['assigned_to__last_name']
            df['Email'] = df['assigned_to__email']
            
            # Calculate additional metrics
            df['Resolution Rate (%)'] = df['resolution_rate'].round(2)
            df['High Priority Resolution Rate (%)'] = (
                df['high_priority_resolved'] * 100.0 / df['high_priority_total']
            ).round(2).fillna(0)
            df['Conversion Rate (%)'] = (
                df['conversion_count'] * 100.0 / df['convertible_queries']
            ).round(2).fillna(0)
            
            # Format average response time
            df['Average Response Time'] = df['avg_response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Select and order columns
            df = df[[
                'Staff Member',
                'Email',
                'total_queries',
                'resolved_queries',
                'Resolution Rate (%)',
                'Average Response Time',
                'high_priority_total',
                'high_priority_resolved',
                'High Priority Resolution Rate (%)',
                'avg_satisfaction',
                'rated_queries',
                'Conversion Rate (%)'
            ]]
            
            # Rename columns for better readability
            df.rename(columns={
                'total_queries': 'Total Queries',
                'resolved_queries': 'Resolved Queries',
                'high_priority_total': 'High Priority Queries',
                'high_priority_resolved': 'High Priority Resolved',
                'avg_satisfaction': 'Average Satisfaction (1-5)',
                'rated_queries': 'Number of Rated Queries'
            }, inplace=True)

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066cc',
                'font_color': 'white'
            })

            # Write sheet
            df.to_excel(excel_file, sheet_name='Staff Performance Metrics', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Staff Performance Metrics']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                if not df.empty:
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    )
                else:
                    max_length = len(str(value))
                worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file