import pandas as pd
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from query_management.models import Query
from datetime import datetime

class ConversionReportGenerator:
    """Handles generation of Conversion related reports"""
    
    @staticmethod
    def generate_conversion_by_type(start_date, end_date):
        """Generates analysis of conversion rates across different query types"""
        # Get base queryset for queries with conversion status
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            conversion_status__isnull=False
        )

        # Get conversion metrics by query type
        conversion_metrics = list(queries.values(
            'query_type'
        ).annotate(
            total_queries=Count('query_id'),
            converted=Count('query_id', filter=Q(conversion_status=True)),
            avg_response_time=Avg('response_time'),
            avg_satisfaction=Avg('satisfaction_rating', filter=Q(satisfaction_rating__isnull=False))
        ).order_by('-converted'))

        # Create DataFrame
        df = pd.DataFrame(conversion_metrics)
        
        if not df.empty:
            # Map query types to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            df['query_type'] = df['query_type'].map(type_mapping)
            
            # Handle null values in query_type
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Calculate conversion rate
            df['conversion_rate'] = (df['converted'] * 100.0 / df['total_queries']).round(2)
            
            # Format time durations
            df['avg_response_time'] = df['avg_response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction scores
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            
            # Rename columns for better readability
            df.rename(columns={
                'query_type': 'Query Type',
                'total_queries': 'Total Queries',
                'converted': 'Converted to Patient',
                'conversion_rate': 'Conversion Rate (%)',
                'avg_response_time': 'Average Response Time',
                'avg_satisfaction': 'Average Satisfaction (1-5)'
            }, inplace=True)

            # Reorder columns
            df = df[[
                'Query Type',
                'Total Queries',
                'Converted to Patient',
                'Conversion Rate (%)',
                'Average Response Time',
                'Average Satisfaction (1-5)'
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
            df.to_excel(excel_file, sheet_name='Conversion Analysis', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Conversion Analysis']
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
    def generate_patient_conversion_tracking(start_date, end_date):
        """Generates detailed tracking report of query to patient conversions"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset for converted queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            conversion_status__isnull=False
        ).values(
            'query_id',
            'subject',
            'created_at',
            'query_type',
            'source',
            'priority',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'conversion_status',
            'response_time',
            'satisfaction_rating',
            'is_patient',
            'resolved_at'
        ).order_by('-created_at')

        # Create DataFrame
        df = pd.DataFrame(list(queries))
        
        if not df.empty:
            # Convert timezone-aware datetimes to timezone-naive
            for field in ['created_at', 'resolved_at']:
                df[field] = pd.to_datetime(df[field]).apply(
                    lambda x: x.astimezone(local_tz).replace(tzinfo=None) if pd.notnull(x) else x
                )
            
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)

            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Create staff member full name
            df['Handled By'] = df['assigned_to__first_name'].fillna('') + ' ' + df['assigned_to__last_name'].fillna('')
            df['Handled By'] = df['Handled By'].replace('', 'Unassigned')
            
            # Format response time
            df['response_time'] = df['response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Calculate conversion time
            df['conversion_time'] = df['resolved_at'] - df['created_at']
            df['Time to Convert'] = df['conversion_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Create conversion status labels
            df['Conversion Status'] = df['conversion_status'].map({
                True: 'Converted to Patient',
                False: 'Not Converted'
            })
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            df['satisfaction_rating'].fillna('No Rating', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_id': 'Query ID',
                'subject': 'Subject',
                'created_at': 'Created Date',
                'query_type': 'Query Type',
                'source': 'Source',
                'priority': 'Priority',
                'response_time': 'Response Time',
                'satisfaction_rating': 'Satisfaction Rating',
                'resolved_at': 'Resolution Date',
                'is_patient': 'Is Existing Patient'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query ID',
                'Subject',
                'Created Date',
                'Resolution Date',
                'Query Type',
                'Source',
                'Priority',
                'Handled By',
                'Response Time',
                'Time to Convert',
                'Conversion Status',
                'Is Existing Patient',
                'Satisfaction Rating'
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
            df.to_excel(excel_file, sheet_name='Conversion Tracking', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Conversion Tracking']
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
    def generate_source_conversion_analysis(start_date, end_date):
        """Generates analysis of conversions by query source"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            conversion_status__isnull=False
        )

        # Get conversion metrics by source
        source_metrics = list(queries.values(
            'source'
        ).annotate(
            total_queries=Count('query_id'),
            converted=Count('query_id', filter=Q(conversion_status=True)),
            avg_response_time=Avg('response_time'),
            avg_satisfaction=Avg('satisfaction_rating', filter=Q(satisfaction_rating__isnull=False)),
            # Conversion timeline metrics
            same_day_conversion=Count('query_id', 
                filter=Q(
                    conversion_status=True,
                    resolved_at__date=models.F('created_at__date')
                )
            ),
            conversion_time_avg=Avg(
                models.F('resolved_at') - models.F('created_at'),
                filter=Q(conversion_status=True)
            )
        ).order_by('-converted'))  # Changed from '-conversion_rate' to '-converted'

        # Create DataFrame
        df = pd.DataFrame(source_metrics)
        
        if not df.empty:
            # Map source codes to their display names
            source_mapping = dict(Query.SOURCE_CHOICES)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate conversion rate and same day percentage
            df['conversion_rate'] = (df['converted'] * 100.0 / df['total_queries']).round(2)
            df['same_day_percent'] = (df['same_day_conversion'] * 100.0 / df['converted']).round(2)
            
            # Sort by conversion rate after calculation
            df = df.sort_values('conversion_rate', ascending=False)
            
            # Format time durations
            df['avg_response_time'] = df['avg_response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            df['avg_conversion_time'] = df['conversion_time_avg'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction scores
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            
            # Rename columns for better readability
            df.rename(columns={
                'source': 'Query Source',
                'total_queries': 'Total Queries',
                'converted': 'Conversions',
                'conversion_rate': 'Conversion Rate (%)',
                'same_day_conversion': 'Same Day Conversions',
                'same_day_percent': 'Same Day Conversion (%)',
                'avg_response_time': 'Average Response Time',
                'avg_conversion_time': 'Average Time to Convert',
                'avg_satisfaction': 'Average Satisfaction (1-5)'
            }, inplace=True)

            # Select and order columns
            df = df[[
                'Query Source',
                'Total Queries',
                'Conversions',
                'Conversion Rate (%)',
                'Same Day Conversions',
                'Same Day Conversion (%)',
                'Average Response Time',
                'Average Time to Convert',
                'Average Satisfaction (1-5)'
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
            df.to_excel(excel_file, sheet_name='Source Conversion Analysis', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Source Conversion Analysis']
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
    def generate_followup_conversion_timeline(start_date, end_date):
        """Generates timeline analysis of follow-up to conversion process"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset for queries with follow-ups
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            follow_up_date__isnull=False,
            conversion_status__isnull=False
        ).values(
            'query_id',
            'subject',
            'created_at',
            'follow_up_date',
            'resolved_at',
            'query_type',
            'source',
            'priority',
            'assigned_to__first_name',
            'assigned_to__last_name',
            'conversion_status',
            'response_time',
            'satisfaction_rating'
        ).order_by('follow_up_date')

        # Create DataFrame
        df = pd.DataFrame(list(queries))
        
        if not df.empty:
            # Convert timezone-aware datetimes to timezone-naive
            for field in ['created_at', 'follow_up_date', 'resolved_at']:
                df[field] = pd.to_datetime(df[field]).apply(
                    lambda x: x.astimezone(local_tz).replace(tzinfo=None) if pd.notnull(x) else x
                )
            
            # Calculate timeline metrics
            df['time_to_followup'] = df['follow_up_date'] - df['created_at']
            df['followup_to_conversion'] = df['resolved_at'] - df['follow_up_date']
            df['total_conversion_time'] = df['resolved_at'] - df['created_at']
            
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Create staff member full name
            df['Handled By'] = df['assigned_to__first_name'].fillna('') + ' ' + df['assigned_to__last_name'].fillna('')
            df['Handled By'] = df['Handled By'].replace('', 'Unassigned')
            
            # Format time durations
            for col in ['time_to_followup', 'followup_to_conversion', 'total_conversion_time', 'response_time']:
                df[col] = df[col].apply(
                    lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
                )
            
            # Create conversion status labels
            df['Conversion Status'] = df['conversion_status'].map({
                True: 'Converted',
                False: 'Not Converted'
            })
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            df['satisfaction_rating'] = df['satisfaction_rating'].fillna('No Rating')
            
            # Rename columns
            df.rename(columns={
                'query_id': 'Query ID',
                'subject': 'Subject',
                'created_at': 'Created Date',
                'follow_up_date': 'Follow-up Date',
                'resolved_at': 'Conversion Date',
                'query_type': 'Query Type',
                'source': 'Source',
                'priority': 'Priority',
                'time_to_followup': 'Time to Follow-up',
                'followup_to_conversion': 'Follow-up to Conversion',
                'total_conversion_time': 'Total Conversion Time',
                'response_time': 'Initial Response Time',
                'satisfaction_rating': 'Satisfaction Rating'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query ID',
                'Subject',
                'Created Date',
                'Follow-up Date',
                'Conversion Date',
                'Time to Follow-up',
                'Follow-up to Conversion',
                'Total Conversion Time',
                'Initial Response Time',
                'Query Type',
                'Source',
                'Priority',
                'Handled By',
                'Conversion Status',
                'Satisfaction Rating'
            ]]

        # Create unique filename and Excel file
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
            df.to_excel(excel_file, sheet_name='Conversion Timeline', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Conversion Timeline']
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
