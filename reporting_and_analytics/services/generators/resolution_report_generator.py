import pandas as pd
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from query_management.models import Query
from datetime import datetime

class ResolutionReportGenerator:
    """Handles generation of Resolution related reports"""
    
    @staticmethod
    def generate_resolution_summary(start_date, end_date):
        """Generates overview analysis of query resolution patterns"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Calculate overall resolution metrics
        total_queries = queries.count()
        resolved_queries = queries.filter(status='RESOLVED').count()
        resolution_rate = (resolved_queries * 100.0 / total_queries) if total_queries > 0 else 0

        # Get resolution metrics by different dimensions
        resolution_metrics = list(queries.values(
            'query_type',
            'priority',
            'source'
        ).annotate(
            total_count=Count('query_id'),
            resolved_count=Count('query_id', filter=Q(status='RESOLVED')),
            avg_resolution_time=Avg('response_time', filter=Q(status='RESOLVED')),
            first_attempt_resolution=Count('query_id', 
                filter=Q(status='RESOLVED', updates__isnull=True)),
            same_day_resolution=Count('query_id',
                filter=Q(
                    status='RESOLVED',
                    resolved_at__date=models.F('created_at__date')
                )),
            satisfaction_avg=Avg('satisfaction_rating', 
                filter=Q(status='RESOLVED', satisfaction_rating__isnull=False))
        ).order_by('-total_count'))

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
            df['resolution_rate'] = (df['resolved_count'] * 100.0 / df['total_count']).round(2)
            df['first_attempt_rate'] = (df['first_attempt_resolution'] * 100.0 / df['resolved_count']).round(2)
            df['same_day_rate'] = (df['same_day_resolution'] * 100.0 / df['resolved_count']).round(2)
            
            # Format resolution time
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction scores
            df['satisfaction_avg'] = df['satisfaction_avg'].round(2)
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_count': 'Total Queries',
                'resolved_count': 'Resolved Queries',
                'resolution_rate': 'Resolution Rate (%)',
                'first_attempt_rate': 'First Contact Resolution (%)',
                'same_day_rate': 'Same Day Resolution (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'satisfaction_avg': 'Average Satisfaction (1-5)'
            }, inplace=True)

            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Source',
                'Total Queries',
                'Resolved Queries',
                'Resolution Rate (%)',
                'First Contact Resolution (%)',
                'Same Day Resolution (%)',
                'Average Resolution Time',
                'Average Satisfaction (1-5)'
            ]]

        # Create summary DataFrame
        summary_df = pd.DataFrame([{
            'Metric': 'Overall Statistics',
            'Total Queries': total_queries,
            'Resolved Queries': resolved_queries,
            'Resolution Rate (%)': round(resolution_rate, 2),
            'Average Resolution Time': str(
                queries.filter(status='RESOLVED').aggregate(
                    avg=Avg('response_time')
                )['avg']).split('.')[0] if resolved_queries > 0 else 'N/A'
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
    def generate_resolution_patterns(start_date, end_date):
        """Generates analysis of typical resolution approaches and patterns"""
        # Get base queryset for resolved queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='RESOLVED'
        )

        # Get resolution patterns by query characteristics
        pattern_metrics = list(queries.values(
            'query_type',
            'source',
            'priority'
        ).annotate(
            total_resolved=Count('query_id'),
            # Response patterns - count updates directly
            updates_count=Count('updates'),
            single_response_resolution=Count('query_id', 
                filter=Q(updates__isnull=True)
            ),
            # Time patterns
            avg_resolution_time=Avg('response_time'),
            same_day_resolution=Count('query_id',
                filter=Q(resolved_at__date=models.F('created_at__date'))
            ),
            # Resolution quality
            avg_satisfaction=Avg('satisfaction_rating', 
                filter=Q(satisfaction_rating__isnull=False)
            ),
            conversion_count=Count('query_id', filter=Q(conversion_status=True)),
            # Resolution success
            reopened_count=Count('query_id',
                filter=Q(status='RESOLVED') & ~Q(updates__created_at__lt=models.F('resolved_at'))
            )
        ).order_by('-total_resolved'))

        # Create DataFrame
        df = pd.DataFrame(pattern_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)

            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Calculate average updates per query
            df['avg_updates'] = (df['updates_count'] / df['total_resolved']).round(2)
            
            # Calculate percentages
            df['single_response_rate'] = (df['single_response_resolution'] * 100.0 / df['total_resolved']).round(2)
            df['same_day_rate'] = (df['same_day_resolution'] * 100.0 / df['total_resolved']).round(2)
            df['reopened_rate'] = (df['reopened_count'] * 100.0 / df['total_resolved']).round(2)
            df['conversion_rate'] = (df['conversion_count'] * 100.0 / df['total_resolved']).round(2)
            
            # Format time durations and averages
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'source': 'Source',
                'priority': 'Priority',
                'total_resolved': 'Total Resolved',
                'avg_updates': 'Average Interactions',
                'single_response_rate': 'First Contact Resolution (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'same_day_rate': 'Same Day Resolution (%)',
                'avg_satisfaction': 'Average Satisfaction (1-5)',
                'conversion_rate': 'Conversion Rate (%)',
                'reopened_rate': 'Reopened Rate (%)'
            }, inplace=True)

            # Select and order columns
            df = df[[
                'Query Type',
                'Source',
                'Priority',
                'Total Resolved',
                'Average Interactions',
                'First Contact Resolution (%)',
                'Same Day Resolution (%)',
                'Average Resolution Time',
                'Reopened Rate (%)',
                'Average Satisfaction (1-5)',
                'Conversion Rate (%)'
            ]]

        # Add pattern summary analysis
        summary_metrics = {
            'most_efficient': df.nlargest(3, 'First Contact Resolution (%)')[[
                'Query Type', 'Source', 'First Contact Resolution (%)', 'Average Resolution Time'
            ]].to_dict('records'),
            'most_satisfied': df.nlargest(3, 'Average Satisfaction (1-5)')[[
                'Query Type', 'Source', 'Average Satisfaction (1-5)', 'Average Resolution Time'
            ]].to_dict('records'),
            'most_converted': df.nlargest(3, 'Conversion Rate (%)')[[
                'Query Type', 'Source', 'Conversion Rate (%)', 'Average Resolution Time'
            ]].to_dict('records')
        }

        # Create summary DataFrame
        summary_rows = []
        for category, patterns in summary_metrics.items():
            for i, pattern in enumerate(patterns, 1):
                row = {
                    'Category': category.replace('_', ' ').title(),
                    'Rank': f'#{i}',
                    'Query Type': pattern['Query Type'],
                    'Source': pattern['Source']
                }
                row.update({k: v for k, v in pattern.items() if k not in ['Query Type', 'Source']})
                summary_rows.append(row)
        
        summary_df = pd.DataFrame(summary_rows)

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
            summary_df.to_excel(excel_file, sheet_name='Top Patterns', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Top Patterns', summary_df),
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
    def generate_time_to_resolution_by_type(start_date, end_date):
        """Generates analysis of resolution times across different query types"""
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset for resolved queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='RESOLVED',
            response_time__isnull=False
        )

        # Get resolution time metrics by query type
        resolution_metrics = list(queries.values(
            'query_type'
        ).annotate(
            total_resolved=Count('query_id'),
            avg_resolution_time=Avg('response_time'),
            min_resolution_time=models.Min('response_time'),
            max_resolution_time=models.Max('response_time'),
            # Resolution time brackets
            within_1h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=1))),
            within_4h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=4))),
            within_24h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=24))),
            within_48h=Count('query_id', filter=Q(response_time__lte=timezone.timedelta(hours=48))),
            over_48h=Count('query_id', filter=Q(response_time__gt=timezone.timedelta(hours=48))),
            # Quality metrics
            avg_satisfaction=Avg('satisfaction_rating', filter=Q(satisfaction_rating__isnull=False)),
            first_contact_resolution=Count('query_id', filter=Q(updates__isnull=True))
        ).order_by('avg_resolution_time'))

        # Create DataFrame
        df = pd.DataFrame(resolution_metrics)
        
        if not df.empty:
            # Map query types to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Calculate percentages for time brackets
            for bracket in ['within_1h', 'within_4h', 'within_24h', 'within_48h', 'over_48h']:
                df[f'{bracket}_percent'] = (df[bracket] * 100.0 / df['total_resolved']).round(2)
            
            # Calculate first contact resolution rate
            df['first_contact_rate'] = (df['first_contact_resolution'] * 100.0 / df['total_resolved']).round(2)
            
            # Format time durations
            for col in ['avg_resolution_time', 'min_resolution_time', 'max_resolution_time']:
                df[col] = df[col].apply(lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A')
            
            # Round satisfaction scores
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            
            # Rename columns for better readability
            df.rename(columns={
                'query_type': 'Query Type',
                'total_resolved': 'Total Resolved',
                'avg_resolution_time': 'Average Resolution Time',
                'min_resolution_time': 'Fastest Resolution',
                'max_resolution_time': 'Longest Resolution',
                'within_1h': 'Within 1 Hour',
                'within_1h_percent': 'Within 1 Hour (%)',
                'within_4h_percent': 'Within 4 Hours (%)',
                'within_24h_percent': 'Within 24 Hours (%)',
                'within_48h_percent': 'Within 48 Hours (%)',
                'over_48h_percent': 'Over 48 Hours (%)',
                'avg_satisfaction': 'Average Satisfaction (1-5)',
                'first_contact_resolution': 'First Contact Resolutions',
                'first_contact_rate': 'First Contact Resolution Rate (%)'
            }, inplace=True)
            
            # Select and order columns
            df = df[[
                'Query Type',
                'Total Resolved',
                'Average Resolution Time',
                'Fastest Resolution',
                'Longest Resolution',
                'Within 1 Hour',
                'Within 1 Hour (%)',
                'Within 4 Hours (%)',
                'Within 24 Hours (%)',
                'Within 48 Hours (%)',
                'Over 48 Hours (%)',
                'First Contact Resolution Rate (%)',
                'Average Satisfaction (1-5)'
            ]]

        # Create summary statistics
        summary_df = pd.DataFrame([{
            'Metric': 'Overall Resolution Times',
            'Total Queries Resolved': queries.count(),
            'Average Resolution Time': str(
                queries.aggregate(avg=Avg('response_time'))['avg']
            ).split('.')[0] if queries.exists() else 'N/A',
            'Best Performing Type': df.iloc[0]['Query Type'] if not df.empty else 'N/A',
            'Most Complex Type': df.iloc[-1]['Query Type'] if not df.empty else 'N/A'
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
            summary_df.to_excel(excel_file, sheet_name='Summary', index=False)
            df.to_excel(excel_file, sheet_name='Resolution Time Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Summary', summary_df),
                ('Resolution Time Analysis', df)
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
    def generate_resolution_satisfaction_correlation(start_date, end_date):
        """Generates analysis of correlation between resolution approaches and satisfaction"""
        # Get base queryset for resolved queries with satisfaction ratings
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            status='RESOLVED',
            satisfaction_rating__isnull=False
        )

        # Get satisfaction metrics by different dimensions
        satisfaction_metrics = list(queries.values(
            'query_type',
            'priority',
            'source'
        ).annotate(
            total_rated=Count('query_id'),
            avg_satisfaction=Avg('satisfaction_rating'),
            high_satisfaction=Count('query_id', filter=Q(satisfaction_rating__gte=4)),
            low_satisfaction=Count('query_id', filter=Q(satisfaction_rating__lte=2)),
            # Resolution speed metrics
            avg_resolution_time=Avg('response_time'),
            same_day_resolution=Count('query_id', 
                filter=Q(resolved_at__date=models.F('created_at__date'))
            ),
            # Resolution approach metrics
            first_contact_resolution=Count('query_id', filter=Q(updates__isnull=True)),
            multi_interaction=Count('query_id', filter=Q(updates__isnull=False)),
            update_count=Count('updates')  # Changed from Avg(Count()) to just Count()
        ).order_by('-avg_satisfaction'))

        # Create DataFrame
        df = pd.DataFrame(satisfaction_metrics)
        
        if not df.empty:
            # Map codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)

            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate derived metrics
            df['high_satisfaction_rate'] = (df['high_satisfaction'] * 100.0 / df['total_rated']).round(2)
            df['low_satisfaction_rate'] = (df['low_satisfaction'] * 100.0 / df['total_rated']).round(2)
            df['first_contact_rate'] = (df['first_contact_resolution'] * 100.0 / df['total_rated']).round(2)
            df['same_day_rate'] = (df['same_day_resolution'] * 100.0 / df['total_rated']).round(2)
            
            # Format time durations
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round averages
            df['avg_satisfaction'] = df['avg_satisfaction'].round(2)
            df['avg_interactions'] = (df['update_count'] / df['total_rated']).round(1)
            
            # Handle null values
            df['query_type'].fillna('Unspecified', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'priority': 'Priority',
                'source': 'Source',
                'total_rated': 'Total Rated Queries',
                'avg_satisfaction': 'Average Satisfaction (1-5)',
                'high_satisfaction_rate': 'High Satisfaction Rate (%)',
                'low_satisfaction_rate': 'Low Satisfaction Rate (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'first_contact_rate': 'First Contact Resolution Rate (%)',
                'same_day_rate': 'Same Day Resolution Rate (%)',
                'avg_interactions': 'Average Interactions'
            }, inplace=True)

            # Select and order columns
            df = df[[
                'Query Type',
                'Priority',
                'Source',
                'Total Rated Queries',
                'Average Satisfaction (1-5)',
                'High Satisfaction Rate (%)',
                'Low Satisfaction Rate (%)',
                'First Contact Resolution Rate (%)',
                'Same Day Resolution Rate (%)',
                'Average Resolution Time',
                'Average Interactions'
            ]]

        # Create correlation insights using pandas correlation instead of database correlation
        if not df.empty:
            # Get raw data for correlation analysis
            raw_data = pd.DataFrame(list(queries.values(
                'satisfaction_rating',
                'response_time'
            ))).assign(
                update_count=queries.annotate(
                    updates_count=Count('updates')
                ).values_list('updates_count', flat=True)
            )

            # Calculate correlations
            correlation_data = []
            if len(raw_data) > 1:  # Need at least 2 points for correlation
                # Response time correlation
                response_time_corr = raw_data['satisfaction_rating'].corr(
                    pd.to_timedelta(raw_data['response_time']).dt.total_seconds()
                )
                
                # Updates correlation
                updates_corr = raw_data['satisfaction_rating'].corr(
                    raw_data['update_count']
                )
                
                correlation_data = [
                    {'Metric': 'Resolution Time', 'Correlation with Satisfaction': response_time_corr},
                    {'Metric': 'Number of Interactions', 'Correlation with Satisfaction': updates_corr}
                ]

            correlation_df = pd.DataFrame(correlation_data).round(3)
        else:
            correlation_df = pd.DataFrame(columns=['Metric', 'Correlation with Satisfaction'])

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
            correlation_df.to_excel(excel_file, sheet_name='Satisfaction Correlations', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths for both sheets
            for sheet_name, df in [
                ('Satisfaction Correlations', correlation_df),
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
