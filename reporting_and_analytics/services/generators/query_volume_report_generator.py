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

class QueryVolumeReportGenerator:
    """Handles generation of Query Volume related reports"""
    
    @staticmethod
    def generate_temporal_query_count(start_date, end_date):
        """Generates Daily/Weekly/Monthly Query Count report"""
        
        # Get local timezone
        local_tz = timezone.get_current_timezone()
        
        # Get base queryset within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Create empty DataFrames with correct columns
        df_daily = pd.DataFrame(columns=['Date', 'Number of Queries'])
        df_weekly = pd.DataFrame(columns=['Week Starting', 'Number of Queries'])
        df_monthly = pd.DataFrame(columns=['Month', 'Number of Queries'])

        if queries.exists():
            # Daily counts
            daily_counts = list(queries.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('query_id')
            ).order_by('date'))

            # Weekly counts
            weekly_counts = list(queries.annotate(
                week=TruncWeek('created_at')
            ).values('week').annotate(
                count=Count('query_id')
            ).order_by('week'))

            # Monthly counts
            monthly_counts = list(queries.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('query_id')
            ).order_by('month'))

            # Convert timezone and create DataFrames
            if daily_counts:
                for entry in daily_counts:
                    # Convert date to datetime before timezone conversion
                    if isinstance(entry['date'], datetime):
                        entry['date'] = entry['date'].astimezone(local_tz).replace(tzinfo=None)
                    else:
                        # Convert date to datetime at midnight
                        entry['date'] = datetime.combine(entry['date'], datetime.min.time())
                df_daily = pd.DataFrame(daily_counts)
                df_daily.rename(columns={'date': 'Date', 'count': 'Number of Queries'}, inplace=True)

            if weekly_counts:
                for entry in weekly_counts:
                    if isinstance(entry['week'], datetime):
                        entry['week'] = entry['week'].astimezone(local_tz).replace(tzinfo=None)
                    else:
                        entry['week'] = datetime.combine(entry['week'], datetime.min.time())
                df_weekly = pd.DataFrame(weekly_counts)
                df_weekly.rename(columns={'week': 'Week Starting', 'count': 'Number of Queries'}, inplace=True)

            if monthly_counts:
                for entry in monthly_counts:
                    if isinstance(entry['month'], datetime):
                        entry['month'] = entry['month'].astimezone(local_tz).replace(tzinfo=None)
                    else:
                        entry['month'] = datetime.combine(entry['month'], datetime.min.time())
                df_monthly = pd.DataFrame(monthly_counts)
                df_monthly.rename(columns={'month': 'Month', 'count': 'Number of Queries'}, inplace=True)

        # Create unique filename using naive datetime
        temp_file = f'temp_report_{datetime.combine(start_date.date(), datetime.min.time()).strftime("%Y%m%d")}_{datetime.combine(end_date.date(), datetime.min.time()).strftime("%Y%m%d")}.xlsx'
        
        # Use context manager
        with pd.ExcelWriter(temp_file, engine='xlsxwriter') as excel_file:
            workbook = excel_file.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066cc',
                'font_color': 'white'
            })

            # Write sheets
            df_daily.to_excel(excel_file, sheet_name='Daily Counts', index=False)
            df_weekly.to_excel(excel_file, sheet_name='Weekly Counts', index=False)
            df_monthly.to_excel(excel_file, sheet_name='Monthly Counts', index=False)

            # Format headers and adjust column widths
            for sheet_name, df in [
                ('Daily Counts', df_daily),
                ('Weekly Counts', df_weekly),
                ('Monthly Counts', df_monthly)
            ]:
                worksheet = excel_file.sheets[sheet_name]
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    # Adjust column width based on content
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
    def generate_source_distribution(start_date, end_date):
        """Generates Query Source Distribution report"""
        # Get base queryset within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Get source distribution
        source_counts = list(queries.values('source').annotate(
            count=Count('query_id')
        ).order_by('-count'))

        # Create DataFrame
        df = pd.DataFrame(source_counts)
        
        if not df.empty:
            # Map source codes to their display names
            source_mapping = dict(Query.SOURCE_CHOICES)
            df['source'] = df['source'].map(source_mapping)
            df.rename(columns={'source': 'Source', 'count': 'Number of Queries'}, inplace=True)

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
            df.to_excel(excel_file, sheet_name='Source Distribution', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Source Distribution']
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
    def generate_type_distribution(start_date, end_date):
        """Generates Query Type Distribution report"""
        # Get base queryset within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Get type distribution
        type_counts = list(queries.values('query_type').annotate(
            count=Count('query_id')
        ).order_by('-count'))

        # Create DataFrame
        df = pd.DataFrame(type_counts)
        
        if not df.empty:
            # Map type codes to their display names
            type_mapping = dict(Query.QUERY_TYPE_CHOICES)
            df['query_type'] = df['query_type'].map(type_mapping)
            df.rename(columns={'query_type': 'Query Type', 'count': 'Number of Queries'}, inplace=True)
            
            # Handle null/None values in query_type
            df['Query Type'].fillna('Unspecified', inplace=True)

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
            df.to_excel(excel_file, sheet_name='Query Type Distribution', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['Query Type Distribution']
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
    def generate_user_type_distribution(start_date, end_date):
        """Generates Anonymous vs Registered User Query Distribution report"""
        # Get base queryset within date range
        queries = Query.objects.filter(
            created_at__range=(start_date, end_date)
        )

        # Get distribution by user type
        user_type_counts = list(queries.values('is_anonymous').annotate(
            count=Count('query_id')
        ).order_by('-count'))

        # Create DataFrame
        df = pd.DataFrame(user_type_counts)
        
        if not df.empty:
            # Map boolean values to readable labels
            df['is_anonymous'] = df['is_anonymous'].map({True: 'Anonymous', False: 'Registered User'})
            df.rename(columns={'is_anonymous': 'User Type', 'count': 'Number of Queries'}, inplace=True)

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
            df.to_excel(excel_file, sheet_name='User Type Distribution', index=False)

            # Format headers and adjust column widths
            worksheet = excel_file.sheets['User Type Distribution']
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