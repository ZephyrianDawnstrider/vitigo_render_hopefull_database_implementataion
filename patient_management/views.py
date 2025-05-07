# Standard library imports
import logging

# Django core imports
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView
from django.contrib import messages

# Local application imports
from access_control.models import Role
from patient_management.models import Patient
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from .models import (
    Patient,
    VitiligoAssessment, 
    TreatmentPlan,
    Medication,
    MedicalHistory
)
from .forms import PatientRegistrationForm, PatientProfileForm, MedicalHistoryForm

# Configure logging and user model
User = get_user_model()
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

class PatientListView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'patient_management'):
            messages.error(request, "You don't have permission to access patient management")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('patient_list.html', self.request.user.role, 'patient_management')

    def get(self, request):
        try:
            patient_role = Role.objects.get(name='PATIENT')
            
            if request.user.role == patient_role:
                messages.error(request, "Patients cannot access this page")
                return handler403(request, exception="Access Denied")

            # Get all patients using the foreign key relationship
            patients = User.objects.filter(role=patient_role).order_by('-date_joined')
            
            # Apply filters
            status = request.GET.get('status')
            search_query = request.GET.get('search')

            if status:
                patients = patients.filter(is_active=(status == 'active'))
            
            if search_query:
                patients = patients.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(patient_profile__phone_number__icontains=search_query)
                )

            # Pagination
            page_size = int(request.GET.get('page_size', 10))  # Default 10 items per page
            paginator = Paginator(patients, page_size)
            page = request.GET.get('page')

            try:
                patients = paginator.page(page)
            except PageNotAnInteger:
                patients = paginator.page(1)
            except EmptyPage:
                patients = paginator.page(paginator.num_pages)

            # Get metrics
            total_patients = User.objects.filter(role=patient_role).count()
            active_patients = User.objects.filter(role=patient_role, is_active=True).count()
            inactive_patients = User.objects.filter(role=patient_role, is_active=False).count()
            
            new_patients_this_month = User.objects.filter(
                role=patient_role,
                date_joined__month=timezone.now().month,
                date_joined__year=timezone.now().year
            ).count()

            context = {
                'patients': patients,
                'total_patients': total_patients,
                'active_patients': active_patients,
                'inactive_patients': inactive_patients,
                'new_patients_this_month': new_patients_this_month,
                'paginator': paginator,
                'is_paginated': True if paginator.num_pages > 1 else False,
                'page_obj': patients,
                'user_role': request.user.role,
                'current_status': status,
                'search_query': search_query,
                'page_size': page_size,
            }

            return render(request, self.get_template_name(), context)
            
        except Exception as e:
            logger.error(f"Error in PatientListView: {str(e)}", exc_info=True)
            messages.error(request, "An unexpected error occurred while loading patients")
            return handler500(request, exception=e)


class PatientDetailView(LoginRequiredMixin, DetailView):
    def get_template_name(self):
        return get_template_path('patient_detail.html', self.request.user.role, 'patient_management')

    def get_template_names(self):
        return [self.get_template_name()]

    def get_object(self):
        try:
            return get_object_or_404(User, id=self.kwargs.get('user_id'))
        except Http404:
            logger.error(f"User with id {self.kwargs.get('user_id')} not found")
            messages.error(self.request, "User not found")
            raise

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        try:
            context['patient_profile'] = Patient.objects.get(user=user)
            context['has_profile'] = True
            
            # Try to get related data
            try:
                context['medical_history'] = context['patient_profile'].medical_history
            except MedicalHistory.DoesNotExist:
                context['medical_history'] = None
                
            context['latest_assessment'] = VitiligoAssessment.objects.filter(
                patient=context['patient_profile']
            ).order_by('-assessment_date').first()
            
            context['active_treatment'] = TreatmentPlan.objects.filter(
                patient=context['patient_profile']
            ).order_by('-created_date').first()
            
            context['current_medications'] = Medication.objects.filter(
                patient=context['patient_profile'],
                end_date__isnull=True
            ).order_by('-start_date')
            
        except Patient.DoesNotExist:
            context['has_profile'] = False
            context['patient_profile'] = None
            context['medical_history'] = None
            context['latest_assessment'] = None
            context['active_treatment'] = None
            context['current_medications'] = []
            
        return context


class PatientRegistrationView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'patient_management'):
            messages.error(request, "You don't have permission to register patients")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('patient_registration.html', self.request.user.role, 'patient_management')

    def get(self, request):
        form = PatientRegistrationForm()
        return render(request, self.get_template_name(), {'form': form})

    def post(self, request):
        form = PatientRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                patient_role = Role.objects.get(name='PATIENT')
                user = form.save(commit=False)
                user.role = patient_role
                user.save()
                form.save()  # This will create the patient profile and medical history
                
                messages.success(request, "Patient registered successfully")
                return redirect('patient_list')
            except Exception as e:
                logger.error(f"Error in patient registration: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred during registration")
                return render(request, self.get_template_name(), {'form': form})
        
        return render(request, self.get_template_name(), {'form': form})


class CreatePatientProfileView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'patient_management'):
            messages.error(request, "You don't have permission to create patient profiles")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('create_patient_profile.html', self.request.user.role, 'patient_management')

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Check if profile already exists
            if hasattr(user, 'patient_profile'):
                messages.error(request, "Patient profile already exists")
                return redirect('patient_detail', user_id=user_id)
            
            profile_form = PatientProfileForm()
            medical_history_form = MedicalHistoryForm()
            
            return render(request, self.get_template_name(), {
                'user': user,
                'profile_form': profile_form,
                'medical_history_form': medical_history_form
            })
            
        except Exception as e:
            logger.error(f"Error in CreatePatientProfileView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the form")
            return redirect('patient_detail', user_id=user_id)

    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            
            profile_form = PatientProfileForm(request.POST)
            medical_history_form = MedicalHistoryForm(request.POST)
            
            if profile_form.is_valid() and medical_history_form.is_valid():
                # Create patient profile
                patient = profile_form.save(commit=False)
                patient.user = user
                patient.save()
                
                # Create medical history
                medical_history = medical_history_form.save(commit=False)
                medical_history.patient = patient
                medical_history.save()
                
                messages.success(request, "Patient profile created successfully")
                return redirect('patient_detail', user_id=user_id)
                
            return render(request, self.get_template_name(), {
                'user': user,
                'profile_form': profile_form,
                'medical_history_form': medical_history_form
            })
            
        except Exception as e:
            logger.error(f"Error in CreatePatientProfileView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while creating the profile")
            return redirect('patient_detail', user_id=user_id)


class EditPatientProfileView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'patient_management'):
            messages.error(request, "You don't have permission to edit patient profiles")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('edit_patient_profile.html', self.request.user.role, 'patient_management')

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = get_object_or_404(Patient, user=user)
            
            profile_form = PatientProfileForm(instance=patient)
            medical_history_form = MedicalHistoryForm(instance=patient.medical_history)
            
            return render(request, self.get_template_name(), {
                'user': user,
                'profile_form': profile_form,
                'medical_history_form': medical_history_form
            })
            
        except Exception as e:
            logger.error(f"Error in EditPatientProfileView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the profile")
            return redirect('patient_detail', user_id=user_id)

    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = get_object_or_404(Patient, user=user)
            
            profile_form = PatientProfileForm(request.POST, instance=patient)
            medical_history_form = MedicalHistoryForm(request.POST, instance=patient.medical_history)
            
            if profile_form.is_valid() and medical_history_form.is_valid():
                profile_form.save()
                medical_history_form.save()
                
                messages.success(request, "Patient profile updated successfully")
                return redirect('patient_detail', user_id=user_id)
                
            return render(request, self.get_template_name(), {
                'user': user,
                'profile_form': profile_form,
                'medical_history_form': medical_history_form
            })
            
        except Exception as e:
            logger.error(f"Error in EditPatientProfileView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while updating the profile")
            return redirect('patient_detail', user_id=user_id)


class DeactivatePatientView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            user.is_active = False
            user.save()
            
            messages.success(request, f'Successfully deactivated patient: {user.get_full_name()}')
            return redirect('patient_list')
            
        except Exception as e:
            logger.error(f"Error deactivating patient: {str(e)}")
            messages.error(request, 'Failed to deactivate patient')
            return redirect('patient_list')


class ActivatePatientView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            user.is_active = True
            user.save()
            
            messages.success(request, f'Successfully activated patient: {user.get_full_name()}')
            return redirect('patient_list')
            
        except Exception as e:
            logger.error(f"Error activating patient: {str(e)}")
            messages.error(request, 'Failed to activate patient')
            return redirect('patient_list')