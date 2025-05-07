import pandas as pd
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from query_management.models import Query
from datetime import datetime

class PriorityReportGenerator:
    """Handles generation of Priority based reports"""
    
    @staticmethod
    def generate_high_priority_status(start_date, end_date):
        """Generates detailed status report for high priority queries"""
        current_time = timezone.now()
        
        # Get base queryset for high priority queries
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            priority='A'  # High priority
        )

        # Calculate metrics by status
        status_metrics = list(queries.values(
            'query_type',
            'source',
            'status'
        ).annotate(
            total_count=Count('query_id'),
            avg_response_time=Avg(models.F('updated_at') - models.F('created_at')),
            overdue_count=Count('query_id', 
                filter=Q(expected_response_date__lt=current_time)
            ),
            unassigned_count=Count('query_id', 
                filter=Q(assigned_to__isnull=True)
            ),
            resolution_time=Avg('response_time', 
                filter=Q(status__in=['RESOLVED', 'CLOSED'])
            )
        ).order_by('query_type', 'source', 'status'))

        # Create DataFrame
        df = pd.DataFrame(status_metrics)
        
        if not df.empty:
            # Map codes to display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            status_mapping = dict(Query.STATUS_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            df['status'] = df['status'].map(status_mapping)
            
            # Calculate percentages
            df['overdue_rate'] = (df['overdue_count'] * 100.0 / df['total_count']).round(2)
            df['unassigned_rate'] = (df['unassigned_count'] * 100.0 / df['total_count']).round(2)
            
            # Format durations
            for col in ['avg_response_time', 'resolution_time']:
                df[col] = df[col].apply(
                    lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
                )
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'source': 'Source',
                'status': 'Status',
                'total_count': 'Total Queries',
                'avg_response_time': 'Avg Response Time',
                'overdue_count': 'Overdue',
                'overdue_rate': 'Overdue Rate (%)',
                'unassigned_count': 'Unassigned',
                'unassigned_rate': 'Unassigned Rate (%)',
                'resolution_time': 'Resolution Time'
            }, inplace=True)

        # Generate summary metrics
        total_high_priority = queries.count()
        summary_df = pd.DataFrame([{
            'Metric': 'High Priority Overview',
            'Total Queries': total_high_priority,
            'New': queries.filter(status='NEW').count(),
            'In Progress': queries.filter(status='IN_PROGRESS').count(),
            'Waiting': queries.filter(status='WAITING').count(),
            'Resolved': queries.filter(status='RESOLVED').count(),
            'Closed': queries.filter(status='CLOSED').count(),
            'Overdue': queries.filter(expected_response_date__lt=current_time).count(),
            'Unassigned': queries.filter(assigned_to__isnull=True).count(),
            'Avg Resolution Time': str(
                queries.filter(
                    status__in=['RESOLVED', 'CLOSED']
                ).aggregate(
                    avg=Avg('response_time')
                )['avg'] or 'N/A'
            ).split('.')[0]
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#FF4444',  # Red background for high priority
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Overview', index=False)
            df.to_excel(excel_file, sheet_name='Detailed Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Overview', summary_df), ('Detailed Analysis', df)]:
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
    def generate_priority_distribution(start_date, end_date):
        """Generates analysis of query priority distribution and metrics"""
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Calculate priority distribution metrics
        priority_metrics = list(queries.values(
            'priority',
            'query_type',
            'source'
        ).annotate(
            total_count=Count('query_id'),
            resolved_count=Count('query_id', 
                filter=Q(status__in=['RESOLVED', 'CLOSED'])
            ),
            overdue_count=Count('query_id', 
                filter=Q(expected_response_date__lt=current_time)
            ),
            avg_response_time=Avg('response_time'),
            satisfaction_avg=Avg('satisfaction_rating')
        ).order_by('priority', 'query_type', 'source'))

        # Create DataFrame
        df = pd.DataFrame(priority_metrics)
        
        if not df.empty:
            # Map codes to display names
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            
            # Apply mappings
            df['priority'] = df['priority'].map(priority_mapping)
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            
            # Calculate percentages and rates
            total_queries = df['total_count'].sum()
            df['distribution_percent'] = (df['total_count'] * 100.0 / total_queries).round(2)
            df['resolution_rate'] = (df['resolved_count'] * 100.0 / df['total_count']).round(2)
            df['overdue_rate'] = (df['overdue_count'] * 100.0 / df['total_count']).round(2)
            
            # Format time durations
            df['avg_response_time'] = df['avg_response_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Round satisfaction average
            df['satisfaction_avg'] = df['satisfaction_avg'].round(2)
            
            # Rename columns
            df.rename(columns={
                'priority': 'Priority Level',
                'query_type': 'Query Type',
                'source': 'Source',
                'total_count': 'Total Queries',
                'distribution_percent': 'Distribution (%)',
                'resolved_count': 'Resolved',
                'resolution_rate': 'Resolution Rate (%)',
                'overdue_count': 'Overdue',
                'overdue_rate': 'Overdue Rate (%)',
                'avg_response_time': 'Avg Response Time',
                'satisfaction_avg': 'Avg Satisfaction'
            }, inplace=True)

        # Generate priority summary
        summary_df = pd.DataFrame([{
            'Metric': 'Priority Distribution Overview',
            'Total Queries': queries.count(),
            'High Priority (%)': round(queries.filter(priority='A').count() * 100.0 / queries.count(), 2),
            'Medium Priority (%)': round(queries.filter(priority='B').count() * 100.0 / queries.count(), 2),
            'Low Priority (%)': round(queries.filter(priority='C').count() * 100.0 / queries.count(), 2),
            'Overall Resolution Rate (%)': round(
                queries.filter(status__in=['RESOLVED', 'CLOSED']).count() * 100.0 / queries.count(), 2
            ),
            'Overall Satisfaction': round(
                queries.filter(satisfaction_rating__isnull=False).aggregate(
                    avg=Avg('satisfaction_rating')
                )['avg'] or 0, 2
            )
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',  # Green background
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Overview', index=False)
            df.to_excel(excel_file, sheet_name='Priority Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Overview', summary_df), ('Priority Analysis', df)]:
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
    def generate_sla_compliance_report(start_date, end_date):
        """Generates SLA compliance analysis by priority level"""
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Calculate SLA metrics by priority
        sla_metrics = list(queries.values(
            'priority',
            'query_type'
        ).annotate(
            total_queries=Count('query_id'),
            within_sla=Count('query_id', 
                filter=Q(
                    resolved_at__lt=models.F('expected_response_date'),
                    status__in=['RESOLVED', 'CLOSED']
                )
            ),
            breached_sla=Count('query_id', 
                filter=Q(
                    expected_response_date__lt=current_time
                ) & ~Q(status__in=['RESOLVED', 'CLOSED'])  # Fixed: using ~Q instead of not_in
            ),
            avg_breach_time=Avg(
                models.F('resolved_at') - models.F('expected_response_date'),
                filter=Q(
                    resolved_at__gt=models.F('expected_response_date'),
                    status__in=['RESOLVED', 'CLOSED']
                )
            ),
            first_response_within_sla=Count('query_id',
                filter=Q(updates__isnull=False) & 
                      Q(updates__created_at__lt=models.F('expected_response_date'))
            )
        ).order_by('priority', 'query_type'))

        # Create DataFrame
        df = pd.DataFrame(sla_metrics)
        
        if not df.empty:
            # Map codes to display names
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            
            # Apply mappings
            df['priority'] = df['priority'].map(priority_mapping)
            df['query_type'] = df['query_type'].map(type_mapping)
            
            # Calculate rates
            df['sla_compliance_rate'] = (df['within_sla'] * 100.0 / df['total_queries']).round(2)
            df['sla_breach_rate'] = (df['breached_sla'] * 100.0 / df['total_queries']).round(2)
            df['first_response_compliance'] = (df['first_response_within_sla'] * 100.0 / df['total_queries']).round(2)
            
            # Format breach time
            df['avg_breach_time'] = df['avg_breach_time'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Rename columns
            df.rename(columns={
                'priority': 'Priority Level',
                'query_type': 'Query Type',
                'total_queries': 'Total Queries',
                'within_sla': 'Within SLA',
                'breached_sla': 'SLA Breached',
                'sla_compliance_rate': 'SLA Compliance Rate (%)',
                'sla_breach_rate': 'SLA Breach Rate (%)',
                'avg_breach_time': 'Average Breach Duration',
                'first_response_compliance': 'First Response Within SLA (%)'
            }, inplace=True)

        # Generate summary metrics
        total_queries = queries.count()
        summary_df = pd.DataFrame([{
            'Metric': 'Overall SLA Compliance',
            'Total Queries': total_queries,
            'Overall Compliance Rate (%)': round(
                queries.filter(
                    resolved_at__lt=models.F('expected_response_date'),
                    status__in=['RESOLVED', 'CLOSED']
                ).count() * 100.0 / total_queries, 2
            ),
            'High Priority Compliance (%)': round(
                queries.filter(
                    priority='A',
                    resolved_at__lt=models.F('expected_response_date'),
                    status__in=['RESOLVED', 'CLOSED']
                ).count() * 100.0 / queries.filter(priority='A').count(), 2
            ),
            'Current SLA Breaches': queries.filter(
                expected_response_date__lt=current_time
            ).exclude(  # Fixed: using exclude instead of not_in
                status__in=['RESOLVED', 'CLOSED']
            ).count(),
            'Average Breach Duration': str(
                queries.filter(
                    resolved_at__gt=models.F('expected_response_date'),
                    status__in=['RESOLVED', 'CLOSED']
                ).aggregate(
                    avg=Avg(models.F('resolved_at') - models.F('expected_response_date'))
                )['avg'] or 'N/A'
            ).split('.')[0]
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#FFA500',  # Orange background for SLA
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='SLA Overview', index=False)
            df.to_excel(excel_file, sheet_name='SLA Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('SLA Overview', summary_df), ('SLA Analysis', df)]:
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
    def generate_priority_escalation_tracking(start_date, end_date):
        """Generates analysis of query priority escalation patterns"""
        current_time = timezone.now()
        
        # Get base queryset
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date),
            updates__isnull=False  # Only queries with updates
        ).distinct()

        # Calculate escalation metrics
        escalation_metrics = list(queries.values(
            'query_type',
            'source',
            'priority'
        ).annotate(
            total_queries=Count('query_id', distinct=True),
            escalated_count=Count(
                'query_id',
                filter=Q(
                    updates__content__contains='priority changed'
                ) & Q(
                    updates__content__contains='increased'
                ),
                distinct=True
            ),
            avg_time_to_escalation=Avg(
                models.F('updates__created_at') - models.F('created_at'),
                filter=Q(
                    updates__content__contains='priority changed'
                ) & Q(
                    updates__content__contains='increased'
                )
            ),
            multiple_escalations=Count(
                'query_id',
                filter=Q(
                    updates__content__contains='priority changed'
                ) & Q(
                    updates__content__contains='increased'
                ),
                distinct=True
            ) - 1,  # Subtract first escalation
            resolved_after_escalation=Count(
                'query_id',
                filter=Q(
                    status__in=['RESOLVED', 'CLOSED']
                ) & Q(
                    updates__content__contains='priority changed'
                ),
                distinct=True
            )
        ).order_by('query_type', 'source', 'priority'))

        # Create DataFrame
        df = pd.DataFrame(escalation_metrics)
        
        if not df.empty:
            # Map codes to display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            source_mapping = dict(Query.SOURCE_CHOICES)
            priority_mapping = dict(Query.PRIORITY_CHOICES)
            
            # Apply mappings
            df['query_type'] = df['query_type'].map(type_mapping)
            df['source'] = df['source'].map(source_mapping)
            df['priority'] = df['priority'].map(priority_mapping)
            
            # Calculate percentages
            df['escalation_rate'] = (df['escalated_count'] * 100.0 / df['total_queries']).round(2)
            df['multiple_escalation_rate'] = (df['multiple_escalations'] * 100.0 / df['escalated_count']).round(2)
            df['resolution_rate_after_escalation'] = (df['resolved_after_escalation'] * 100.0 / df['escalated_count']).round(2)
            
            # Format time durations
            df['avg_time_to_escalation'] = df['avg_time_to_escalation'].apply(
                lambda x: str(x).split('.')[0] if pd.notnull(x) else 'N/A'
            )
            
            # Rename columns
            df.rename(columns={
                'query_type': 'Query Type',
                'source': 'Source',
                'priority': 'Initial Priority',
                'total_queries': 'Total Queries',
                'escalated_count': 'Escalated Queries',
                'escalation_rate': 'Escalation Rate (%)',
                'avg_time_to_escalation': 'Avg Time to Escalation',
                'multiple_escalations': 'Multiple Escalations',
                'multiple_escalation_rate': 'Multiple Escalation Rate (%)',
                'resolved_after_escalation': 'Resolved After Escalation',
                'resolution_rate_after_escalation': 'Post-Escalation Resolution Rate (%)'
            }, inplace=True)

        # Generate summary metrics
        total_queries = queries.count()
        total_escalated = queries.filter(
            Q(updates__content__contains='priority changed') & 
            Q(updates__content__contains='increased')
        ).distinct().count()

        summary_df = pd.DataFrame([{
            'Metric': 'Priority Escalation Overview',
            'Total Queries': total_queries,
            'Total Escalated': total_escalated,
            'Overall Escalation Rate (%)': round(total_escalated * 100.0 / total_queries if total_queries > 0 else 0, 2),
            'Multiple Escalations': queries.filter(
                Q(updates__content__contains='priority changed') & 
                Q(updates__content__contains='increased')
            ).distinct().count() - total_escalated,
            'Average Time to Escalation': str(
                queries.filter(
                    Q(updates__content__contains='priority changed') & 
                    Q(updates__content__contains='increased')
                ).aggregate(
                    avg=Avg(models.F('updates__created_at') - models.F('created_at'))
                )['avg'] or 'N/A'
            ).split('.')[0],
            'Resolution Rate After Escalation (%)': round(
                queries.filter(
                    status__in=['RESOLVED', 'CLOSED'],
                    updates__content__contains='priority changed'
                ).distinct().count() * 100.0 / total_escalated if total_escalated > 0 else 0, 2
            )
        }])

        # Create unique filename
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Write to Excel
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#9C27B0',  # Purple background for escalation
                'font_color': 'white'
            })

            # Write sheets
            summary_df.to_excel(excel_file, sheet_name='Escalation Overview', index=False)
            df.to_excel(excel_file, sheet_name='Escalation Analysis', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [('Escalation Overview', summary_df), ('Escalation Analysis', df)]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    max_length = max(
                        df[df.columns[col_num]].astype(str).apply(len).max(),
                        len(str(value))
                    ) if not df.empty else len(str(value))
                    worksheet.set_column(col_num, col_num, max_length + 2)

        return temp_file
