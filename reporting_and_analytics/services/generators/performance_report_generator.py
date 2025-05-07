import pandas as pd
from django.db import models
from django.db.models import Avg, Count, Q
from django.utils import timezone
from query_management.models import Query
from datetime import datetime

class PerformanceReportGenerator:
    """Handles generation of Performance related reports"""
    
    @staticmethod
    def generate_response_time_by_priority(start_date, end_date):
        """Generates report analyzing response times based on priority levels"""
        # Get base queryset for resolved queries with response time
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='RESOLVED',
            response_time__isnull=False
        )

        # Get metrics by priority
        priority_metrics = list(queries.values(
            'priority'
        ).annotate(
            total_queries=Count('query_id'),
            avg_response_time=Avg('response_time'),
            min_response_time=models.Min('response_time'),
            max_response_time=models.Max('response_time'),
            within_24h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=24))),
            within_48h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=48))),
            over_48h=Count('query_id', filter=Q(response_time__gt=timezone.timedelta(hours=48)))
        ).order_by('priority'))

        # Create DataFrame
        df = pd.DataFrame(priority_metrics)
        
        if not df.empty:
            # Map priority codes to their display names
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Calculate percentage metrics
            df['within_24h_percent'] = (df['within_24h'] * 100.0 / df['total_queries']).round(2)
            df['within_48h_percent'] = (df['within_48h'] * 100.0 / df['total_queries']).round(2)
            df['over_48h_percent'] = (df['over_48h'] * 100.0 / df['total_queries']).round(2)
            
            # Format time durations
            for col in ['avg_response_time', 'min_response_time', 'max_response_time']:
                df[col] = df[col].apply(lambda x: str(x).split('.')[0])
            
            # Rename columns for better readability
            df.rename(columns={
                'priority': 'Priority',
                'total_queries': 'Total Queries',
                'avg_response_time': 'Average Response Time',
                'min_response_time': 'Minimum Response Time',
                'max_response_time': 'Maximum Response Time',
                'within_24h': 'Resolved within 24h',
                'within_48h': 'Resolved within 48h',
                'over_48h': 'Resolved after 48h',
                'within_24h_percent': 'Within 24h (%)',
                'within_48h_percent': 'Within 48h (%)',
                'over_48h_percent': 'Over 48h (%)'
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
            df.to_excel(excel_file, sheet_name='Response Time Analysis', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Response Time Analysis']
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
    def generate_resolution_time_analysis(start_date, end_date):
        """Generates detailed breakdown of query resolution times"""
        # Get base queryset for resolved queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='RESOLVED',
            response_time__isnull=False
        )

        # Get detailed resolution metrics
        resolution_metrics = list(queries.values(
            'query_type',
            'priority'
        ).annotate(
            total_queries=Count('query_id'),
            avg_resolution_time=Avg('response_time'),
            min_resolution_time=models.Min('response_time'),
            max_resolution_time=models.Max('response_time'),
            # Time brackets
            under_1h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=1))),
            under_4h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=4))),
            under_8h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=8))),
            under_24h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=24))),
            under_48h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=48))),
            over_48h=Count('query_id', filter=Q(response_time__gt=timezone.timedelta(hours=48))),
            # Customer satisfaction for resolved queries
            avg_satisfaction=Avg('satisfaction_rating', filter=Q(satisfaction_rating__isnull=False))
        ).order_by('query_type', 'priority'))

        # Create DataFrame
        df = pd.DataFrame(resolution_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Handle null values in query_type
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Format time durations
            for col in ['avg_resolution_time', 'min_resolution_time', 'max_resolution_time']:
                df[col] = df[col].apply(lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A')
            
            # Calculate percentage distributions
            time_brackets = ['under_1h', 'under_4h', 'under_8h', 'under_24h', 'under_48h', 'over_48h']
            for bracket in time_brackets:
                df[f'{bracket}_percent'] = (df[bracket] * 100.0 / df['total_queries']).round(2)
            
            # Round satisfaction scores
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            
            # Rename columns for better readability
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'total_queries': 'Total Queries',
                'avg_resolution_time': 'Average Resolution Time',
                'min_resolution_time': 'Minimum Resolution Time',
                'max_resolution_time': 'Maximum Resolution Time',
                'under_1h': 'Under 1 Hour',
                'under_4h': 'Under 4 Hours',
                'under_8h': 'Under 8 Hours',
                'under_24h': 'Under 24 Hours',
                'under_48h': 'Under 48 Hours',
                'over_48h': 'Over 48 Hours',
                'under_1h_percent': 'Under 1 Hour (%)',
                'under_4h_percent': 'Under 4 Hours (%)',
                'under_8h_percent': 'Under 8 Hours (%)',
                'under_24h_percent': 'Under 24 Hours (%)',
                'under_48h_percent': 'Under 48 Hours (%)',
                'over_48h_percent': 'Over 48 Hours (%)',
                'avg_satisfaction': 'Average Satisfaction (1-5)'
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
            df.to_excel(excel_file, sheet_name='Resolution Time Analysis', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Resolution Time Analysis']
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
    def generate_overdue_queries_report(start_date, end_date):
        """Generates report of queries that are past their expected response date"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        current_time = timezone.now()
        
        # Get base queryset for overdue queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            expected_response_date__lt=current_time,
            status__in=['NEW', 'IN_PROGRESS', 'WAITING']
        ).values(
            'query_id',
            'subject',
            'created_at',
            'expected_response_date',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'priority',
            'query_type',
            'status',
            'source'
        ).order_by('expected_response_date')

        # Create DataFrame
        df = pd.DataFrame(list(queries))
        
        if not df.empty:
            # Convert timezone-aware datetimes to timezone-naive
            df['created_at'] = pd.to_datetime(df['created_at']).apply(
                lambda x: x.astimezone(local_tz).replace(tzinfo=None) if pd.notnull(x) else x
            )
            df['expected_response_date'] = pd.to_datetime(df['expected_response_date']).apply(
                lambda x: x.astimezone(local_tz).replace(tzinfo=None) if pd.notnull(x) else x
            )
            
            # Map codes to their display names
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            status_mapping = dict(Query.STATUS_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)

            # Apply mappings
            df['priority'] = df['priority'].map(priority_mapping)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['status'] = df['status'].map(status_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Create staff member full name
            df['Assigned To'] = df['assigned_to__first_name'].fillna('') + ' ' + df['assigned_to__last_name'].fillna('')
            df['Assigned To'] = df['Assigned To'].replace('', 'Unassigned')
            
            # Calculate overdue duration with timezone-naive datetimes
            current_time_naive = current_time.astimezone(local_tz).replace(tzinfo=None)
            df['overdue_duration'] = current_time_naive - df['expected_response_date']
            df['Overdue By'] = df['overdue_duration'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename and reorder columns
            df.rename(columns={
                'query_id': 'Query ID',
                'subject': 'Subject',
                'created_at': 'Created Date',
                'expected_response_date': 'Expected Response Date',
                'priority': 'Priority',
                'query_type': 'Query Type',
                'status': 'Status',
                'source': 'Source'
            }, inplace=True)
            
            # Select final columns
            df = df[[
                'Query ID',
                'Subject',
                'Created Date',
                'Expected Response Date',
                'Overdue By',
                'Priority',
                'Status',
                'Query Type',
                'Source',
                'Assigned To'
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
            df.to_excel(excel_file, sheet_name='Overdue Queries', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Overdue Queries']
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
    def generate_pending_followups_list(start_date, end_date):
        """Generates report of queries that require follow-up"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        current_time = timezone.now()
        
        # Get base queryset for queries requiring follow-up
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            follow_up_date__isnull=False,
            follow_up_date__lte=current_time,
            status__in=['NEW', 'IN_PROGRESS', 'WAITING']
        ).values(
            'query_id',
            'subject',
            'created_at',
            'follow_up_date',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'priority',
            'query_type',
            'status',
            'source',
            'description'
        ).order_by('follow_up_date')

        # Create DataFrame
        df = pd.DataFrame(list(queries))
        
        if not df.empty:
            # Convert timezone-aware datetimes to timezone-naive
            for field in ['created_at', 'follow_up_date']:
                df[field] = pd.to_datetime(df[field]).apply(
                    lambda x: x.astimezone(local_tz).replace(tzinfo=None) if pd.notnull(x) else x
                )
            
            # Map codes to their display names
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            status_mapping = dict(Query.STATUS_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)

            # Apply mappings
            df['priority'] = df['priority'].map(priority_mapping)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['status'] = df['status'].map(status_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Create staff member full name
            df['Assigned To'] = df['assigned_to__first_name'].fillna('') + ' ' + df['assigned_to__last_name'].fillna('')
            df['Assigned To'] = df['Assigned To'].replace('', 'Unassigned')
            
            # Calculate delay duration
            current_time_naive = current_time.astimezone(local_tz).replace(tzinfo=None)
            df['delay_duration'] = current_time_naive - df['follow_up_date']
            df['Delay'] = df['delay_duration'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_id': 'Query ID',
                'subject': 'Subject',
                'created_at': 'Created Date',
                'follow_up_date': 'Follow-up Due Date',
                'priority': 'Priority',
                'query_type': 'Query Type',
                'status': 'Status',
                'source': 'Source',
                'description': 'Description'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query ID',
                'Subject',
                'Description',
                'Created Date',
                'Follow-up Due Date',
                'Delay',
                'Priority',
                'Status',
                'Query Type',
                'Source',
                'Assigned To'
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
            df.to_excel(excel_file, sheet_name='Pending Follow-ups', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Pending Follow-ups']
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
    def generate_satisfaction_ratings_summary(start_date, end_date):
        """Generates comprehensive analysis of user satisfaction ratings"""
        # Get base queryset for queries with satisfaction ratings
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            satisfaction_rating__isnull=False
        )

        # Get overall satisfaction metrics
        overall_metrics = {
            'total_rated': queries.count(),
            'avg_rating': queries.aggregate(avg=models.Avg('satisfaction_rating'))['avg'],
            'rating_distribution': dict(queries.values('satisfaction_rating')
                                     .annotate(count=Count('query_id'))
                                     .values_list('satisfaction_rating', 'count'))
        }

        # Get satisfaction metrics by various dimensions
        dimension_metrics = list(queries.values(
            'query_type',
            'priority',
            'source',
            'assigned_to__first_name',
            'assigned_to__last_name'
        ).annotate(
            total_queries=Count('query_id'),
            avg_satisfaction=models.Avg('satisfaction_rating'),
            response_time_avg=models.Avg('response_time'),
            high_satisfaction=Count('query_id', filter=Q(satisfaction_rating__gte=4)),
            low_satisfaction=Count('query_id', filter=Q(satisfaction_rating__lte=2))
        ).order_by('-avg_satisfaction'))

        # Create DataFrames
        df_dimensions = pd.DataFrame(dimension_metrics)
        
        if not df_dimensions.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)

            # Apply mappings
            df_dimensions['query_type'] = df_dimensions['query_type'].map(type_mapping)
            df_dimensions['priority'] = df_dimensions['priority'].map(priority_mapping)
            df_dimensions['source'] = df_dimensions['source'].map(source_mapping)
            
            # Create staff member full name
            df_dimensions['Staff Member'] = (
                df_dimensions['assigned_to__first_name'].fillna('') + ' ' + 
                df_dimensions['assigned_to__last_name'].fillna('')
            ).replace('', 'Unassigned')
            
            # Calculate percentages
            df_dimensions['High Satisfaction Rate (%)'] = (
                df_dimensions['high_satisfaction'] * 100.0 / df_dimensions['total_queries']
            ).round(2)
            df_dimensions['Low Satisfaction Rate (%)'] = (
                df_dimensions['low_satisfaction'] * 100.0 / df_dimensions['total_queries']
            ).round(2)
            
            # Format response times
            df_dimensions['Average Response Time'] = df_dimensions['response_time_avg'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Rename columns
            df_dimensions.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_queries': 'Total Rated Queries',
                'avg_satisfaction': 'Average Rating'
            }, inplace=True)
            
            # Round average satisfaction scores
            df_dimensions['Average Rating'] = df_dimensions['Average Rating'].round(2)
            
            # Select and order columns
            df_dimensions = df_dimensions[[
                'Query Type',
                'Priority',
                'Source',
                'Staff Member',
                'Total Rated Queries',
                'Average Rating',
                'High Satisfaction Rate (%)',
                'Low Satisfaction Rate (%)',
                'Average Response Time'
            ]]

        # Create overall summary DataFrame
        overall_summary = pd.DataFrame([{
            'Metric': 'Overall Statistics',
            'Total Rated Queries': overall_metrics['total_rated'],
            'Average Rating': round(overall_metrics['avg_rating'], 2) if overall_metrics['avg_rating'] else 'N/A',
            '5 Star Ratings': overall_metrics['rating_distribution'].get(5, 0),
            '4 Star Ratings': overall_metrics['rating_distribution'].get(4, 0),
            '3 Star Ratings': overall_metrics['rating_distribution'].get(3, 0),
            '2 Star Ratings': overall_metrics['rating_distribution'].get(2, 0),
            '1 Star Ratings': overall_metrics['rating_distribution'].get(1, 0)
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
            overall_summary.to_excel(excel_file, sheet_name='Overall Summary', index=False)
            df_dimensions.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Overall Summary', overall_summary),
                ('Detailed Analysis', df_dimensions)
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
