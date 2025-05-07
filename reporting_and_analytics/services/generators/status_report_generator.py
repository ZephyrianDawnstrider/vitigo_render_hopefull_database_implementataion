import pandas as pd
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from query_management.models import Query
from datetime import datetime

class StatusReportGenerator:
    """Handles generation of Status based reports"""
    
    @staticmethod
    def generate_open_queries_summary(start_date, end_date):
        """Generates overview analysis of new and in-progress queries"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        current_time = timezone.now()
        
        # Get base queryset for open queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status__in=['NEW', 'IN_PROGRESS', 'WAITING']
        )

        # Calculate overall metrics
        total_open = queries.count()
        new_queries = queries.filter(status='NEW').count()
        in_progress = queries.filter(status='IN_PROGRESS').count()
        waiting = queries.filter(status='WAITING').count()
        overdue = queries.filter(expected_response_date__lt=current_time).count()

        # Get detailed metrics by type and priority
        detailed_metrics = list(queries.values(
            'query_type',
            'priority'
        ).annotate(
            total_count=Count('query_id'),
            new_count=Count('query_id', filter=Q(status='NEW')),
            in_progress_count=Count('query_id', filter=Q(status='IN_PROGRESS')),
            waiting_count=Count('query_id', filter=Q(status='WAITING')),
            overdue_count=Count('query_id', filter=Q(expected_response_date__lt=current_time)),
            avg_age=Avg(current_time - models.F('created_at')),
            unassigned=Count('query_id', filter=Q(assigned_to__isnull=True))
        ).order_by('-total_count'))

        # Create DataFrame
        df = pd.DataFrame(detailed_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Calculate percentages
            df['new_percent'] = (df['new_count'] * 100.0 / df['total_count']).round(2)
            df['overdue_percent'] = (df['overdue_count'] * 100.0 / df['total_count']).round(2)
            df['unassigned_percent'] = (df['unassigned'] * 100.0 / df['total_count']).round(2)
            
            # Format average age
            df['avg_age'] = df['avg_age'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'total_count': 'Total Open',
                'new_count': 'New',
                'in_progress_count': 'In Progress',
                'waiting_count': 'Waiting',
                'overdue_count': 'Overdue',
                'new_percent': 'New Queries (%)',
                'overdue_percent': 'Overdue (%)',
                'unassigned_percent': 'Unassigned (%)',
                'avg_age': 'Average Age',
                'unassigned': 'Unassigned'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Total Open',
                'New',
                'In Progress',
                'Waiting',
                'Overdue',
                'New Queries (%)',
                'Overdue (%)',
                'Unassigned',
                'Unassigned (%)',
                'Average Age'
            ]]

        # Create summary DataFrame
        summary_df = pd.DataFrame([{
            'Metric': 'Overall Open Queries',
            'Total Open': total_open,
            'New': new_queries,
            'In Progress': in_progress,
            'Waiting': waiting,
            'Overdue': overdue,
            'New Rate (%)': round(new_queries * 100.0 / total_open, 2) if total_open > 0 else 0,
            'Overdue Rate (%)': round(overdue * 100.0 / total_open, 2) if total_open > 0 else 0,
            'Average Age': str(
                queries.aggregate(
                    avg_age=Avg(current_time - models.F('created_at'))
                )['avg_age']
            ).split('.')[0] if total_open > 0 else 'N/A'
        }])

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

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Overall Summary', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Overall Summary', summary_df),
                ('Detailed Analysis', df)
            ]:
                worksheet = excel_file.sheets[sheet_name]
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
    def generate_stalled_queries_analysis(start_date, end_date):
        """Generates analysis of queries stuck in waiting status"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        current_time = timezone.now()
        
        # Get base queryset for waiting queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='WAITING'
        )

        # Get detailed metrics for waiting queries
        waiting_metrics = list(queries.values(
            'query_type',
            'priority',
            'source'
        ).annotate(
            total_waiting=Count('query_id'),
            avg_wait_time=Avg(current_time - models.F('created_at')),
            avg_last_update=Avg(current_time - models.F('updated_at')),
            no_updates=Count('query_id', filter=Q(updates__isnull=True)),
            overdue=Count('query_id', filter=Q(expected_response_date__lt=current_time)),
            unassigned=Count('query_id', filter=Q(assigned_to__isnull=True)),
            has_followup=Count('query_id', filter=Q(follow_up_date__isnull=False))
        ).order_by('-total_waiting'))

        # Create DataFrame
        df = pd.DataFrame(waiting_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate percentages
            df['no_updates_percent'] = (df['no_updates'] * 100.0 / df['total_waiting']).round(2)
            df['overdue_percent'] = (df['overdue'] * 100.0 / df['total_waiting']).round(2)
            df['unassigned_percent'] = (df['unassigned'] * 100.0 / df['total_waiting']).round(2)
            df['followup_percent'] = (df['has_followup'] * 100.0 / df['total_waiting']).round(2)
            
            # Format time durations
            for col in ['avg_wait_time', 'avg_last_update']:
                df[col] = df[col].apply(
                    lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
                )
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_waiting': 'Total Waiting',
                'avg_wait_time': 'Average Wait Time',
                'avg_last_update': 'Time Since Last Update',
                'no_updates': 'No Updates',
                'no_updates_percent': 'No Updates (%)',
                'overdue': 'Overdue',
                'overdue_percent': 'Overdue (%)',
                'unassigned': 'Unassigned',
                'unassigned_percent': 'Unassigned (%)',
                'has_followup': 'Has Follow-up',
                'followup_percent': 'Has Follow-up (%)'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Source',
                'Total Waiting',
                'Average Wait Time',
                'Time Since Last Update',
                'No Updates',
                'No Updates (%)',
                'Overdue',
                'Overdue (%)',
                'Unassigned',
                'Unassigned (%)',
                'Has Follow-up',
                'Has Follow-up (%)'
            ]]

        # Create summary metrics
        total_waiting = queries.count()
        summary_df = pd.DataFrame([{
            'Metric': 'Stalled Queries Overview',
            'Total Waiting': total_waiting,
            'Average Wait Time': str(
                queries.aggregate(
                    avg=Avg(current_time - models.F('created_at'))
                )['avg']
            ).split('.')[0] if total_waiting > 0 else 'N/A',
            'Overdue': queries.filter(expected_response_date__lt=current_time).count(),
            'Unassigned': queries.filter(assigned_to__isnull=True).count(),
            'Without Updates': queries.filter(updates__isnull=True).count(),
            'With Follow-up Scheduled': queries.filter(follow_up_date__isnull=False).count()
        }])

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

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Overview', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Overview', summary_df),
                ('Detailed Analysis', df)
            ]:
                worksheet = excel_file.sheets[sheet_name]
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
    def generate_resolution_rate_report(start_date, end_date):
        """Generates analysis of query resolution rates"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Get resolution metrics by dimensions
        resolution_metrics = list(queries.values(
            'query_type',
            'priority',
            'source'
        ).annotate(
            total_queries=Count('query_id'),
            resolved_count=Count('query_id', filter=Q(status='RESOLVED')),
            closed_count=Count('query_id', filter=Q(status='CLOSED')),
            avg_resolution_time=Avg('response_time', filter=Q(status__in=['RESOLVED', 'CLOSED'])),
            same_day_resolution=Count('query_id', 
                filter=Q(
                    status__in=['RESOLVED', 'CLOSED'],
                    resolved_at__date=models.F('created_at__date')
                )
            ),
            within_sla=Count('query_id', 
                filter=Q(
                    status__in=['RESOLVED', 'CLOSED'],
                    resolved_at__lt=models.F('expected_response_date')
                )
            )
        ).order_by('-total_queries'))

        # Create DataFrame
        df = pd.DataFrame(resolution_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate percentages
            df['total_resolved'] = df['resolved_count'] + df['closed_count']
            df['resolution_rate'] = (df['total_resolved'] * 100.0 / df['total_queries']).round(2)
            df['same_day_rate'] = (df['same_day_resolution'] * 100.0 / df['total_resolved']).round(2)
            df['sla_compliance'] = (df['within_sla'] * 100.0 / df['total_resolved']).round(2)
            
            # Format time durations
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_queries': 'Total Queries',
                'resolved_count': 'Resolved',
                'closed_count': 'Closed',
                'total_resolved': 'Total Resolved',
                'resolution_rate': 'Resolution Rate (%)',
                'same_day_rate': 'Same Day Resolution (%)',
                'sla_compliance': 'SLA Compliance (%)',
                'avg_resolution_time': 'Average Resolution Time'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Source',
                'Total Queries',
                'Resolved',
                'Closed',
                'Total Resolved',
                'Resolution Rate (%)',
                'Same Day Resolution (%)',
                'SLA Compliance (%)',
                'Average Resolution Time'
            ]]

        # Create summary metrics
        total_queries = queries.count()
        resolved_queries = queries.filter(status__in=['RESOLVED', 'CLOSED']).count()
        
        summary_df = pd.DataFrame([{
            'Metric': 'Overall Resolution Metrics',
            'Total Queries': total_queries,
            'Total Resolved': resolved_queries,
            'Resolution Rate (%)': round(resolved_queries * 100.0 / total_queries, 2) if total_queries > 0 else 0,
            'Same Day Resolutions': queries.filter(
                status__in=['RESOLVED', 'CLOSED'],
                resolved_at__date=models.F('created_at__date')
            ).count(),
            'SLA Compliant': queries.filter(
                status__in=['RESOLVED', 'CLOSED'],
                resolved_at__lt=models.F('expected_response_date')
            ).count(),
            'Average Resolution Time': str(
                queries.filter(
                    status__in=['RESOLVED', 'CLOSED']
                ).aggregate(
                    avg=Avg('response_time')
                )['avg']
            ).split('.')[0] if resolved_queries > 0 else 'N/A'
        }])

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

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Overall Summary', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Overall Summary', summary_df),
                ('Detailed Analysis', df)
            ]:
                worksheet = excel_file.sheets[sheet_name]
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
    def generate_status_transition_analysis(start_date, end_date):
        """Generates analysis of query lifecycle transitions"""
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Get status transition metrics
        status_metrics = list(queries.values(
            'query_type',
            'priority',
            'source'
        ).annotate(
            total_queries=Count('query_id'),
            # Status counts
            new_count=Count('query_id', filter=Q(status='NEW')),
            in_progress=Count('query_id', filter=Q(status='IN_PROGRESS')),
            waiting=Count('query_id', filter=Q(status='WAITING')),
            resolved=Count('query_id', filter=Q(status='RESOLVED')),
            closed=Count('query_id', filter=Q(status='CLOSED')),
            # Transition times
            avg_new_to_progress=Avg(
                models.F('updated_at') - models.F('created_at'),
                filter=Q(status='IN_PROGRESS')
            ),
            avg_total_resolution=Avg(
                models.F('resolved_at') - models.F('created_at'),
                filter=Q(status__in=['RESOLVED', 'CLOSED'])
            ),
            # Status patterns
            direct_resolution=Count('query_id', 
                filter=Q(updates__isnull=True, status__in=['RESOLVED', 'CLOSED'])
            ),
            # Count queries with multiple updates instead of checking update status
            multiple_transitions=Count('query_id',
                filter=Q(
                    updates__isnull=False,
                    status__in=['RESOLVED', 'CLOSED']
                )
            )
        ).order_by('-total_queries'))

        # Create DataFrame
        df = pd.DataFrame(status_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate percentages
            df['resolution_rate'] = ((df['resolved'] + df['closed']) * 100.0 / df['total_queries']).round(2)
            df['direct_resolution_rate'] = (df['direct_resolution'] * 100.0 / df['total_queries']).round(2)
            df['multiple_transition_rate'] = (df['multiple_transitions'] * 100.0 / df['total_queries']).round(2)
            
            # Calculate status distribution percentages
            for status in ['new_count', 'in_progress', 'waiting', 'resolved', 'closed']:
                df[f'{status}_percent'] = (df[status] * 100.0 / df['total_queries']).round(2)
            
            # Format transition times
            for col in ['avg_new_to_progress', 'avg_total_resolution']:
                df[col] = df[col].apply(
                    lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
                )
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_queries': 'Total Queries',
                'new_count': 'New',
                'in_progress': 'In Progress',
                'waiting': 'Waiting',
                'resolved': 'Resolved',
                'closed': 'Closed',
                'new_count_percent': 'New (%)',
                'in_progress_percent': 'In Progress (%)',
                'waiting_percent': 'Waiting (%)',
                'resolved_percent': 'Resolved (%)',
                'closed_percent': 'Closed (%)',
                'avg_new_to_progress': 'Avg. Time to First Action',
                'avg_total_resolution': 'Avg. Resolution Time',
                'resolution_rate': 'Resolution Rate (%)',
                'direct_resolution_rate': 'Direct Resolution Rate (%)',
                'multiple_transition_rate': 'Multiple Transitions (%)'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Source',
                'Total Queries',
                'New',
                'New (%)',
                'In Progress',
                'In Progress (%)',
                'Waiting',
                'Waiting (%)',
                'Resolved',
                'Resolved (%)',
                'Closed',
                'Closed (%)',
                'Avg. Time to First Action',
                'Avg. Resolution Time',
                'Resolution Rate (%)',
                'Direct Resolution Rate (%)',
                'Multiple Transitions (%)'
            ]]

        # Create summary statistics
        total_queries = queries.count()
        resolved_queries = queries.filter(status__in=['RESOLVED', 'CLOSED']).count()
        
        summary_df = pd.DataFrame([{
            'Metric': 'Status Transition Overview',
            'Total Queries': total_queries,
            'Average Time to First Action': str(
                queries.filter(status__in=['IN_PROGRESS', 'RESOLVED', 'CLOSED']).aggregate(
                    avg=Avg(models.F('updated_at') - models.F('created_at'))
                )['avg']
            ).split('.')[0] if total_queries > 0 else 'N/A',
            'Average Resolution Time': str(
                queries.filter(status__in=['RESOLVED', 'CLOSED']).aggregate(
                    avg=Avg(models.F('resolved_at') - models.F('created_at'))
                )['avg']
            ).split('.')[0] if resolved_queries > 0 else 'N/A',
            'Direct Resolutions': queries.filter(
                updates__isnull=True,
                status__in=['RESOLVED', 'CLOSED']
            ).count(),
            'Multiple Transition Resolutions': queries.filter(
                updates__isnull=False,
                status__in=['RESOLVED', 'CLOSED']
            ).count()
        }])

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

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Status Overview', index=False)
            df.to_excel(excel_file, sheet_name='Transition Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Status Overview', summary_df),
                ('Transition Analysis', df)
            ]:
                worksheet = excel_file.sheets[sheet_name]
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
