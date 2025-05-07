from django.core.management.base import BaseCommand
from django.db import transaction
from access_control.models import Module
from reporting_and_analytics.models import ReportCategory, Report

class Command(BaseCommand):
    help = 'Populate reports and categories for query management module'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                # Get query management module
                module = Module.objects.get(name='query_management')

                # Report categories and their reports
                categories_data = {
                    'Query Volume Reports': {
                        'description': 'Reports related to query volumes and distributions',
                        'reports': [
                            {'name': 'Daily/Weekly/Monthly Query Count', 'description': 'Temporal analysis of query volumes'},
                            {'name': 'Queries by Source', 'description': 'Distribution of queries across different sources'},
                            {'name': 'Queries by Type', 'description': 'Analysis of different types of queries received'},
                            {'name': 'Anonymous vs Registered User Queries', 'description': 'Comparison of query volumes by user type'}
                        ]
                    },
                    'Performance Reports': {
                        'description': 'Reports focusing on query handling performance metrics',
                        'reports': [
                            {'name': 'Average Response Time by Priority', 'description': 'Analysis of response times based on priority levels'},
                            {'name': 'Resolution Time Analysis', 'description': 'Detailed breakdown of query resolution times'},
                            {'name': 'Overdue Queries Report', 'description': 'List of queries past their expected response date'},
                            {'name': 'Pending Follow-ups List', 'description': 'Overview of queries requiring follow-up'},
                            {'name': 'User Satisfaction Ratings Summary', 'description': 'Analysis of user satisfaction metrics'}
                        ]
                    },
                    'Staff/Assignment Reports': {
                        'description': 'Reports related to staff workload and performance',
                        'reports': [
                            {'name': 'Queries per Staff Member', 'description': 'Distribution of queries among staff'},
                            {'name': 'Open Queries by Assigned Staff', 'description': 'Current workload analysis by staff member'},
                            {'name': 'Unassigned Queries List', 'description': 'Overview of queries pending assignment'},
                            {'name': 'Staff Performance Metrics', 'description': 'Comprehensive staff performance analysis'}
                        ]
                    },
                    'Status Based Reports': {
                        'description': 'Reports tracking query status and progression',
                        'reports': [
                            {'name': 'Open Queries Summary', 'description': 'Overview of new and in-progress queries'},
                            {'name': 'Stalled Queries Analysis', 'description': 'Analysis of queries in waiting status'},
                            {'name': 'Resolution Rate Report', 'description': 'Query resolution rate metrics'},
                            {'name': 'Status Transition Analysis', 'description': 'Analysis of query lifecycle transitions'}
                        ]
                    },
                    'Conversion Reports': {
                        'description': 'Reports tracking query to patient conversion metrics',
                        'reports': [
                            {'name': 'Conversion Rate by Query Type', 'description': 'Analysis of conversions across query types'},
                            {'name': 'Patient Conversion Tracking', 'description': 'Tracking of query to patient conversions'},
                            {'name': 'Source-wise Conversion Analysis', 'description': 'Conversion analysis by query source'},
                            {'name': 'Follow-up to Conversion Timeline', 'description': 'Timeline analysis of conversion process'}
                        ]
                    },
                    'Priority Based Reports': {
                        'description': 'Reports focused on query priority metrics',
                        'reports': [
                            {'name': 'High Priority Queries Status', 'description': 'Status tracking of high priority queries'},
                            {'name': 'Priority Distribution Analysis', 'description': 'Analysis of query priority distribution'},
                            {'name': 'SLA Compliance Report', 'description': 'Tracking of SLA compliance metrics'},
                            {'name': 'Priority Escalation Tracking', 'description': 'Analysis of priority escalation patterns'}
                        ]
                    },
                    'Tag Analysis Reports': {
                        'description': 'Reports analyzing query tags and patterns',
                        'reports': [
                            {'name': 'Common Issues/Tags Report', 'description': 'Analysis of frequently occurring tags'},
                            {'name': 'Tag Correlation Analysis', 'description': 'Study of relationships between different tags'},
                            {'name': 'Trending Tags Over Time', 'description': 'Temporal analysis of tag popularity'},
                            {'name': 'Tag Distribution by Source', 'description': 'Analysis of tags across different sources'}
                        ]
                    },
                    'Resolution Reports': {
                        'description': 'Reports focusing on query resolution patterns',
                        'reports': [
                            {'name': 'Resolution Summary Analysis', 'description': 'Overview of query resolution patterns'},
                            {'name': 'Common Resolution Patterns', 'description': 'Analysis of typical resolution approaches'},
                            {'name': 'Time to Resolution by Query Type', 'description': 'Resolution time analysis by query type'},
                            {'name': 'Resolution Satisfaction Correlation', 'description': 'Analysis of resolution quality and satisfaction'}
                        ]
                    }
                }

                # Create categories and reports
                for order, (category_name, category_data) in enumerate(categories_data.items(), 1):
                    category = ReportCategory.objects.create(
                        name=category_name,
                        description=category_data['description'],
                        module=module,
                        order=order,
                        is_active=True
                    )

                    # Create reports for this category
                    for report_order, report_data in enumerate(category_data['reports'], 1):
                        Report.objects.create(
                            category=category,
                            name=report_data['name'],
                            description=report_data['description'],
                            order=report_order,
                            is_active=True
                        )

                self.stdout.write(self.style.SUCCESS('Successfully populated reports data'))

        except Module.DoesNotExist:
            self.stdout.write(self.style.ERROR('Query management module not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
