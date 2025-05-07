import pandas as pd
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from query_management.models import Query, QueryTag
from datetime import datetime

class TagReportGenerator:
    """Handles generation of Tag based analysis reports"""
    
    @staticmethod
    def generate_common_issues_report(start_date, end_date):
        """Generates analysis of frequently occurring tags and associated metrics"""
        current_time = timezone.now()
        
        # Get base queryset for queries with tags
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            tags__isnull=False
        ).distinct()

        # Calculate tag metrics
        tag_metrics = list(QueryTag.objects.filter(
            query__created_at__range=(start_date, end_date)
        ).values(
            'name',  # Add name field to values() 
            'id'     # Add id for distinct counting
        ).annotate(
            total_queries=Count('query', distinct=True),
            resolved_count=Count('query', 
                filter=Q(query__status__in=['RESOLVED', 'CLOSED']),
                distinct=True
            ),
            high_priority_count=Count('query',
                filter=Q(query__priority='A'),
                distinct=True
            ),
            avg_resolution_time=Avg('query__response_time',
                filter=Q(query__status__in=['RESOLVED', 'CLOSED'])
            ),
            satisfaction_avg=Avg('query__satisfaction_rating'),
            source_distribution=Count('query__source', distinct=True)
        ).order_by('-total_queries'))

        # Create DataFrame
        df = pd.DataFrame(tag_metrics)
        
        if not df.empty:
            # Calculate rates and percentages
            total_tagged_queries = queries.count()
            df['occurrence_rate'] = (df['total_queries'] * 100.0 / total_tagged_queries).round(2)
            df['resolution_rate'] = (df['resolved_count'] * 100.0 / df['total_queries']).round(2)
            df['high_priority_rate'] = (df['high_priority_count'] * 100.0 / df['total_queries']).round(2)
            
            # Format time durations
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction average
            df['satisfaction_avg'] = df['satisfaction_avg'].round(2)
            
            # Rename columns
            df.rename(columns={
                'name': 'Tag',  # Map the name field to Tag
                'total_queries': 'Total Occurrences',
                'occurrence_rate': 'Occurrence Rate (%)',
                'resolved_count': 'Resolved Queries',
                'resolution_rate': 'Resolution Rate (%)',
                'high_priority_count': 'High Priority Cases',
                'high_priority_rate': 'High Priority Rate (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'satisfaction_avg': 'Average Satisfaction',
                'source_distribution': 'Different Sources Count'
            }, inplace=True)

        # Generate summary metrics
        total_queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        ).count()

        most_common_tag = QueryTag.objects.filter(
            query__created_at__range=(start_date, end_date)
        ).annotate(
            usage_count=Count('query')
        ).order_by('-usage_count').first()
        
        summary_df = pd.DataFrame([{
            'Metric': 'Tag Analysis Overview',
            'Total Queries': total_queries,
            'Queries with Tags': total_tagged_queries,
            'Tag Usage Rate (%)': round(total_tagged_queries * 100.0 / total_queries, 2),
            'Unique Tags': QueryTag.objects.filter(
                query__created_at__range=(start_date, end_date)
            ).distinct().count(),
            'Most Common Tag': most_common_tag.name if most_common_tag else 'N/A',
            'Average Tags per Query': round(
                Query.objects.filter(
                    created_at__range=(start_date, end_date),
                    tags__isnull=False
                ).annotate(
                    tag_count=Count('tags')
                ).aggregate(avg=Avg('tag_count'))['avg'] or 0,
                2
            )
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2196F3',  # Blue background for tags
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Tag Overview', index=False)
            df.to_excel(excel_file, sheet_name='Tag Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Tag Overview', summary_df), ('Tag Analysis', df)]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    ) if not df.empty else len(str(value))
                    worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_tag_correlation_analysis(start_date, end_date):
        """Generates analysis of tag relationships and co-occurrence patterns"""
        current_time = timezone.now()
        
        # Get base queryset for queries with multiple tags
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            tags__isnull=False
        ).annotate(
            tag_count=Count('tags')
        ).filter(tag_count__gt=1).distinct()

        # Calculate tag co-occurrence metrics
        tag_pairs = []
        all_tags = list(QueryTag.objects.filter(
            query__in=queries
        ).distinct())

        for i, tag1 in enumerate(all_tags):
            for tag2 in all_tags[i+1:]:
                # Fix: Use Q objects to combine multiple tag filters
                co_occurrence = queries.filter(
                    Q(tags=tag1) & Q(tags=tag2)
                ).count()
                
                if co_occurrence > 0:
                    tag_pairs.append({
                        'tag1': tag1.name,
                        'tag2': tag2.name,
                        'co_occurrence': co_occurrence,
                        'resolved_together': queries.filter(
                            Q(tags=tag1) & Q(tags=tag2),
                            status__in=['RESOLVED', 'CLOSED']
                        ).count(),
                        'avg_resolution_time': queries.filter(
                            Q(tags=tag1) & Q(tags=tag2),
                            status__in=['RESOLVED', 'CLOSED']
                        ).aggregate(
                            avg=Avg('response_time')
                        )['avg'],
                        'high_priority_count': queries.filter(
                            Q(tags=tag1) & Q(tags=tag2),
                            priority='A'
                        ).count()
                    })

        # Create DataFrame
        df = pd.DataFrame(tag_pairs)
        
        if not df.empty:
            # Calculate additional metrics
            total_queries = queries.count()
            df['occurrence_rate'] = (df['co_occurrence'] * 100.0 / total_queries).round(2)
            df['resolution_rate'] = (df['resolved_together'] * 100.0 / df['co_occurrence']).round(2)
            df['high_priority_rate'] = (df['high_priority_count'] * 100.0 / df['co_occurrence']).round(2)
            
            # Format time durations
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Rename columns
            df.rename(columns={
                'tag1': 'First Tag',
                'tag2': 'Second Tag',
                'co_occurrence': 'Co-occurrences',
                'occurrence_rate': 'Co-occurrence Rate (%)',
                'resolved_together': 'Resolved Together',
                'resolution_rate': 'Joint Resolution Rate (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'high_priority_count': 'High Priority Cases',
                'high_priority_rate': 'High Priority Rate (%)'
            }, inplace=True)
            
            # Sort by co-occurrence count
            df = df.sort_values('Co-occurrences', ascending=False)

        # Generate summary metrics
        total_tagged = Query.objects.filter(
            created_at__range=(start_date, end_date),
            tags__isnull=False
        ).distinct().count()
        
        summary_df = pd.DataFrame([{
            'Metric': 'Tag Correlation Overview',
            'Total Tagged Queries': total_tagged,
            'Queries with Multiple Tags': queries.count(),
            'Multiple Tags Rate (%)': round(queries.count() * 100.0 / total_tagged if total_tagged > 0 else 0, 2),
            'Unique Tag Pairs': len(tag_pairs),
            'Most Common Pair': f"{df['First Tag'].iloc[0]} + {df['Second Tag'].iloc[0]}" if not df.empty else 'N/A',
            'Average Tags per Query': round(
                queries.aggregate(
                    avg=Avg('tag_count')
                )['avg'] or 0,
                2
            ),
            'Max Tags in Query': queries.aggregate(
                max=models.Max('tag_count')
            )['max'] or 0
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#673AB7',  # Deep Purple for correlations
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Correlation Overview', index=False)
            df.to_excel(excel_file, sheet_name='Tag Pairs Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Correlation Overview', summary_df), ('Tag Pairs Analysis', df)]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    ) if not df.empty else len(str(value))
                    worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_trending_tags_report(start_date, end_date):
        """Generates temporal analysis of tag usage and trends"""
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            tags__isnull=False
        ).distinct()

        # Calculate monthly tag trends
        monthly_trends = list(QueryTag.objects.filter(
            query__created_at__range=(start_date, end_date)
        ).annotate(
            month=models.functions.TruncMonth('query__created_at')
        ).values(
            'name',
            'month'
        ).annotate(
            usage_count=Count('query', distinct=True),
            resolved_count=Count('query', 
                filter=Q(query__status__in=['RESOLVED', 'CLOSED']),
                distinct=True
            ),
            avg_response_time=Avg('query__response_time'),
            satisfaction_avg=Avg('query__satisfaction_rating')
        ).order_by('month', '-usage_count'))

        # Create DataFrame
        df = pd.DataFrame(monthly_trends)
        
        if not df.empty:
            # Calculate month-over-month growth
            df['prev_month_usage'] = df.groupby('name')['usage_count'].shift(1)
            df['growth_rate'] = ((df['usage_count'] - df['prev_month_usage']) * 100.0 / df['prev_month_usage']).round(2)
            
            # Calculate resolution rate
            df['resolution_rate'] = (df['resolved_count'] * 100.0 / df['usage_count']).round(2)
            
            # Format dates and times
            df['month'] = df['month'].dt.strftime('%Y-%m')
            df['avg_response_time'] = df['avg_response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction average
            df['satisfaction_avg'] = df['satisfaction_avg'].round(2)
            
            # Rename columns
            df.rename(columns={
                'name': 'Tag',
                'month': 'Month',
                'usage_count': 'Occurrences',
                'growth_rate': 'MoM Growth (%)',
                'resolved_count': 'Resolved',
                'resolution_rate': 'Resolution Rate (%)',
                'avg_response_time': 'Average Response Time',
                'satisfaction_avg': 'Average Satisfaction'
            }, inplace=True)
            
            # Sort by date and usage count
            df = df.sort_values(['Month', 'Occurrences'], ascending=[True, False])

        # Generate trend summary
        top_trending = df[df['MoM Growth (%)'].notna()].nlargest(5, 'MoM Growth (%)')
        declining = df[df['MoM Growth (%)'].notna()].nsmallest(5, 'MoM Growth (%)')
        
        summary_df = pd.DataFrame([{
            'Metric': 'Tag Trends Overview',
            'Total Tagged Queries': queries.count(),
            'Unique Tags Used': QueryTag.objects.filter(
                query__created_at__range=(start_date, end_date)
            ).distinct().count(),
            'Most Used Tag': df.groupby('Tag')['Occurrences'].sum().idxmax() if not df.empty else 'N/A',
            'Fastest Growing Tag': top_trending['Tag'].iloc[0] if not top_trending.empty else 'N/A',
            'Growth Rate (%)': top_trending['MoM Growth (%)'].iloc[0] if not top_trending.empty else 'N/A',
            'Most Declining Tag': declining['Tag'].iloc[0] if not declining.empty else 'N/A',
            'Decline Rate (%)': declining['MoM Growth (%)'].iloc[0] if not declining.empty else 'N/A'
        }])

        # Create Top Trending and Declining Tags summary
        trend_summary = pd.concat([
            top_trending[['Tag', 'Month', 'Occurrences', 'MoM Growth (%)', 'Resolution Rate (%)']],
            pd.DataFrame([{'Tag': '---', 'Month': '---', 'Occurrences': '---', 'MoM Growth (%)': '---', 'Resolution Rate (%)': '---'}]),
            declining[['Tag', 'Month', 'Occurrences', 'MoM Growth (%)', 'Resolution Rate (%)']]
        ]).reset_index(drop=True)

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3F51B5',  # Indigo background for trends
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Trends Overview', index=False)
            trend_summary.to_excel(excel_file, sheet_name='Top & Bottom Trends', index=False)
            df.to_excel(excel_file, sheet_name='Monthly Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [
                ('Trends Overview', summary_df),
                ('Top & Bottom Trends', trend_summary),
                ('Monthly Analysis', df)
            ]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    ) if not df.empty else len(str(value))
                    worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file

    @staticmethod
    def generate_tag_source_distribution(start_date, end_date):
        """Generates analysis of tag distribution across different query sources"""
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            tags__isnull=False
        ).distinct()

        # Calculate source-wise tag metrics
        source_tag_metrics = list(QueryTag.objects.filter(
            query__created_at__range=(start_date, end_date)
        ).values(
            'name',
            'query__source'  # Include source in grouping
        ).annotate(
            usage_count=Count('query', distinct=True),
            resolved_count=Count('query',
                filter=Q(query__status__in=['RESOLVED', 'CLOSED']),
                distinct=True
            ),
            avg_resolution_time=Avg('query__response_time',
                filter=Q(query__status__in=['RESOLVED', 'CLOSED'])
            ),
            high_priority_count=Count('query',
                filter=Q(query__priority='A'),
                distinct=True
            ),
            satisfaction_avg=Avg('query__satisfaction_rating')
        ).order_by('query__source', '-usage_count'))

        # Create DataFrame
        df = pd.DataFrame(source_tag_metrics)
        
        if not df.empty:
            # Map codes to display names
            source_mapping = dict(Query.SOURCE_CHOICES)
            
            # Apply mapping for source
            df['query__source'] = df['query__source'].map(source_mapping)
            
            # Calculate rates and percentages
            source_totals = df.groupby('query__source')['usage_count'].transform('sum')
            df['usage_rate'] = (df['usage_count'] * 100.0 / source_totals).round(2)
            df['resolution_rate'] = (df['resolved_count'] * 100.0 / df['usage_count']).round(2)
            df['high_priority_rate'] = (df['high_priority_count'] * 100.0 / df['usage_count']).round(2)
            
            # Format durations
            df['avg_resolution_time'] = df['avg_resolution_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction average
            df['satisfaction_avg'] = df['satisfaction_avg'].round(2)
            
            # Rename columns
            df.rename(columns={
                'name': 'Tag',
                'query__source': 'Source',
                'usage_count': 'Usage Count',
                'usage_rate': 'Usage Rate (%)',
                'resolved_count': 'Resolved',
                'resolution_rate': 'Resolution Rate (%)',
                'high_priority_count': 'High Priority',
                'high_priority_rate': 'High Priority Rate (%)',
                'avg_resolution_time': 'Average Resolution Time',
                'satisfaction_avg': 'Average Satisfaction'
            }, inplace=True)
            
            # Sort by source and usage count
            df = df.sort_values(['Source', 'Usage Count'], ascending=[True, False])

        # Generate source summary
        source_summary = pd.DataFrame(queries.values(
            'source'
        ).annotate(
            total_queries=Count('query_id', distinct=True),
            unique_tags=Count('tags', distinct=True),
            avg_tags_per_query=Count('tags') * 1.0 / Count('query_id'),
            resolved_rate=(Count('query_id', 
                filter=Q(status__in=['RESOLVED', 'CLOSED'])) * 100.0 / 
                Count('query_id')
            )
        ).order_by('-total_queries'))

        if not source_summary.empty:
            source_summary['source'] = source_summary['source'].map(source_mapping)
            source_summary['avg_tags_per_query'] = source_summary['avg_tags_per_query'].round(2)
            source_summary['resolved_rate'] = source_summary['resolved_rate'].round(2)
            
            source_summary.rename(columns={
                'source': 'Source',
                'total_queries': 'Total Queries',
                'unique_tags': 'Unique Tags Used',
                'avg_tags_per_query': 'Average Tags per Query',
                'resolved_rate': 'Resolution Rate (%)'
            }, inplace=True)

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#00BCD4',  # Cyan background for source distribution
                'font_color': 'white'
            })

            # Write sheets
            source_summary.to_excel(excel_file, sheet_name='Source Overview', index=False)
            df.to_excel(excel_file, sheet_name='Tag Distribution', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Source Overview', source_summary), ('Tag Distribution', df)]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    ) if not df.empty else len(str(value))
                    worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file
