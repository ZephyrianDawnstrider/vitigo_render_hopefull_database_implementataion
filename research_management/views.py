# Python Standard Library imports
import logging
from datetime import datetime

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    ResearchStudy, 
    StudyProtocol, 
    PatientStudyEnrollment, 
    DataCollectionPoint, 
    ResearchData, 
    AnalysisResult, 
    Publication
)

# Logger configuration
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module=''):
    """
    Resolves template path based on user role.
    Now uses the template_folder from Role model.
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        # Fallback for any legacy code
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    if module:
        return f'{role_folder}/{module}/{base_template}'
    return f'{role_folder}/{base_template}'

class ResearchManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'research_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to access Research Management")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('research_dashboard.html', self.request.user.role, 'research_management')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            # Get filter parameters from URL
            filters = {}
            status = request.GET.get('status')
            date = request.GET.get('date')
            search = request.GET.get('search')
            investigator = request.GET.get('investigator')

            # Base queryset
            research_studies = ResearchStudy.objects.select_related('principal_investigator')
            
            # Apply filters
            if status:
                filters['status'] = status
            if date:
                filters['start_date'] = date
            if investigator:
                filters['principal_investigator_id'] = investigator

            # Apply search
            if search:
                research_studies = research_studies.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(principal_investigator__first_name__icontains=search) |
                    Q(principal_investigator__last_name__icontains=search)
                )

            research_studies = research_studies.filter(**filters)

            # Fetch related data
            study_protocols = StudyProtocol.objects.all()
            patient_enrollments = PatientStudyEnrollment.objects.all()
            data_collection_points = DataCollectionPoint.objects.all()
            research_data = ResearchData.objects.all()
            analysis_results = AnalysisResult.objects.all()
            publications = Publication.objects.all()

            # Calculate statistics
            total_studies = research_studies.count()
            total_enrollments = patient_enrollments.count()
            total_data_points = research_data.count()
            total_analysis_results = analysis_results.count()
            total_publications = publications.count()

            # Pagination
            paginator = Paginator(research_studies, 10)
            page = request.GET.get('page')
            try:
                research_studies = paginator.page(page)
            except PageNotAnInteger:
                research_studies = paginator.page(1)
            except EmptyPage:
                research_studies = paginator.page(paginator.num_pages)

            context = {
                'research_studies': research_studies,
                'study_protocols': study_protocols,
                'patient_enrollments': patient_enrollments,
                'data_collection_points': data_collection_points,
                'research_data': research_data,
                'analysis_results': analysis_results,
                'publications': publications,
                'total_studies': total_studies,
                'total_enrollments': total_enrollments,
                'total_data_points': total_data_points,
                'total_analysis_results': total_analysis_results,
                'total_publications': total_publications,
                'paginator': paginator,
                'page_obj': research_studies,
                'current_filters': {
                    'status': status,
                    'date': date,
                    'investigator': investigator,
                    'search': search
                },
                'user_role': request.user.role,
            }

            return render(request, template_path, context)

        except Exception as e:
            logger.exception(f"Error in ResearchManagementView: {str(e)}")
            return handler500(request, exception=str(e))