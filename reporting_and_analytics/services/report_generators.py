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
from .generators.query_volume_report_generator import QueryVolumeReportGenerator
from .generators.staff_report_generator import StaffReportGenerator
from .generators.performance_report_generator import PerformanceReportGenerator
from .generators.conversion_report_generator import ConversionReportGenerator
from .generators.resolution_report_generator import ResolutionReportGenerator
from .generators.status_report_generator import StatusReportGenerator
from .generators.priority_report_generator import PriorityReportGenerator
from .generators.tag_report_generator import TagReportGenerator

class ReportGeneratorFactory:
    """Factory class to get appropriate report generator based on report type"""
    
    @staticmethod
    def get_generator(report_category, report_name):
        if report_category == "Query Volume Reports":
            if report_name == "Daily/Weekly/Monthly Query Count":
                return QueryVolumeReportGenerator.generate_temporal_query_count
            elif report_name == "Queries by Source":
                return QueryVolumeReportGenerator.generate_source_distribution
            elif report_name == "Queries by Type":
                return QueryVolumeReportGenerator.generate_type_distribution
            elif report_name == "Anonymous vs Registered User Queries":
                return QueryVolumeReportGenerator.generate_user_type_distribution
        elif report_category == "Staff/Assignment Reports":
            if report_name == "Queries per Staff Member":
                return StaffReportGenerator.generate_queries_per_staff
            elif report_name == "Open Queries by Assigned Staff":
                return StaffReportGenerator.generate_open_queries_by_staff
            elif report_name == "Unassigned Queries List":
                return StaffReportGenerator.generate_unassigned_queries_list
            elif report_name == "Staff Performance Metrics":
                return StaffReportGenerator.generate_staff_performance_metrics
        elif report_category == "Performance Reports":
            if report_name == "Average Response Time by Priority":
                return PerformanceReportGenerator.generate_response_time_by_priority
            elif report_name == "Resolution Time Analysis":
                return PerformanceReportGenerator.generate_resolution_time_analysis
            elif report_name == "Overdue Queries Report":
                return PerformanceReportGenerator.generate_overdue_queries_report
            elif report_name == "Pending Follow-ups List":
                return PerformanceReportGenerator.generate_pending_followups_list
            elif report_name == "User Satisfaction Ratings Summary":
                return PerformanceReportGenerator.generate_satisfaction_ratings_summary
        elif report_category == "Conversion Reports":
            if report_name == "Conversion Rate by Query Type":
                return ConversionReportGenerator.generate_conversion_by_type
            elif report_name == "Patient Conversion Tracking":
                return ConversionReportGenerator.generate_patient_conversion_tracking
            elif report_name == "Source-wise Conversion Analysis":
                return ConversionReportGenerator.generate_source_conversion_analysis
            elif report_name == "Follow-up to Conversion Timeline":
                return ConversionReportGenerator.generate_followup_conversion_timeline
        elif report_category == "Resolution Reports":
            if report_name == "Resolution Summary Analysis":
                return ResolutionReportGenerator.generate_resolution_summary
            elif report_name == "Common Resolution Patterns":
                return ResolutionReportGenerator.generate_resolution_patterns
            elif report_name == "Time to Resolution by Query Type":
                return ResolutionReportGenerator.generate_time_to_resolution_by_type
            elif report_name == "Resolution Satisfaction Correlation":
                return ResolutionReportGenerator.generate_resolution_satisfaction_correlation
        elif report_category == "Status Based Reports":
            if report_name == "Open Queries Summary":
                return StatusReportGenerator.generate_open_queries_summary
            elif report_name == "Stalled Queries Analysis":
                return StatusReportGenerator.generate_stalled_queries_analysis
            elif report_name == "Resolution Rate Report":
                return StatusReportGenerator.generate_resolution_rate_report
            elif report_name == "Status Transition Analysis":
                return StatusReportGenerator.generate_status_transition_analysis
        elif report_category == "Priority Based Reports":
            if report_name == "High Priority Queries Status":
                return PriorityReportGenerator.generate_high_priority_status
            elif report_name == "Priority Distribution Analysis":
                return PriorityReportGenerator.generate_priority_distribution
            elif report_name == "SLA Compliance Report":
                return PriorityReportGenerator.generate_sla_compliance_report
            elif report_name == "Priority Escalation Tracking":
                return PriorityReportGenerator.generate_priority_escalation_tracking
        elif report_category == "Tag Analysis Reports":
            if report_name == "Common Issues/Tags Report":
                return TagReportGenerator.generate_common_issues_report
            elif report_name == "Tag Correlation Analysis":
                return TagReportGenerator.generate_tag_correlation_analysis
            elif report_name == "Trending Tags Over Time":
                return TagReportGenerator.generate_trending_tags_report
            elif report_name == "Tag Distribution by Source":
                return TagReportGenerator.generate_tag_source_distribution
        return None
