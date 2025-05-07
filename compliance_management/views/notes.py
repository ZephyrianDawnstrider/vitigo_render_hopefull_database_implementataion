# Standard library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone

# Local/application imports
from access_control.permissions import PermissionManager
from error_handling.views import handler500, handler403
from compliance_management.models import ComplianceNote, ComplianceSchedule
from compliance_management.forms import ComplianceNoteForm
from phototherapy_management.utils import get_template_path

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceNoteListView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied to compliance notes list for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to access compliance notes")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in compliance notes list dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def get(self, request):
        try:
            # Get filter parameters
            schedule_id = request.GET.get('schedule')
            note_type = request.GET.get('type')
            is_private = request.GET.get('private')
            
            # Base queryset with related data
            notes = ComplianceNote.objects.select_related(
                'schedule__patient',
                'created_by'
            ).order_by('-created_at')
            
            # Apply filters
            if schedule_id:
                notes = notes.filter(schedule_id=schedule_id)
            if note_type:
                notes = notes.filter(note_type=note_type)
            if is_private is not None:
                notes = notes.filter(is_private=is_private == 'true')

            context = {
                'notes': notes,
                'note_types': ComplianceNote.NOTE_TYPE_CHOICES,
                'current_filters': {
                    'schedule': schedule_id,
                    'type': note_type,
                    'private': is_private
                }
            }

            template_path = get_template_path(
                'notes/note_list.html',
                request.user.role,
                'compliance_management'
            )

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in compliance notes list view: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the notes")
            return handler500(request, exception=str(e))

class ComplianceNoteCreateView(LoginRequiredMixin, CreateView):
    model = ComplianceNote
    form_class = ComplianceNoteForm
    
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_modify(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied to create compliance note for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to create notes")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in compliance note create dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('compliance_management:compliance_notes_list')

    def get_success_url(self):
        return reverse_lazy('compliance_management:compliance_note_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Compliance note created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating compliance note: {str(e)}")
            messages.error(self.request, "Failed to create compliance note")
            return super().form_invalid(form)

    def get_template_names(self):
        return [get_template_path(
            'notes/note_form.html',
            self.request.user.role,
            'compliance_management'
        )]

class ComplianceNoteUpdateView(LoginRequiredMixin, UpdateView):
    model = ComplianceNote
    form_class = ComplianceNoteForm
    
    def dispatch(self, request, *args, **kwargs):
        try:
            note = self.get_object()
            if not PermissionManager.check_module_modify(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied to update compliance note for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to update notes")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in compliance note update dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('compliance_notes_list')

    def get_success_url(self):
        return reverse_lazy('compliance_management:compliance_note_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        try:
            form.instance.updated_at = timezone.now()
            response = super().form_valid(form)
            messages.success(self.request, "Compliance note updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating compliance note: {str(e)}")
            messages.error(self.request, "Failed to update compliance note")
            return super().form_invalid(form)

    def get_template_names(self):
        return [get_template_path(
            'notes/note_form.html',
            self.request.user.role,
            'compliance_management'
        )]

class ComplianceNoteDetailView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied to view compliance note for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to view notes")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in compliance note detail dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('compliance_management:compliance_notes_list')

    def get(self, request, pk):
        try:
            note = get_object_or_404(
                ComplianceNote.objects.select_related(
                    'schedule__patient',
                    'created_by'
                ),
                pk=pk
            )

            context = {
                'note': note,
                'can_edit': PermissionManager.check_module_modify(
                    request.user,
                    'compliance_management'
                )
            }

            template_path = get_template_path(
                'notes/note_detail.html',
                request.user.role,
                'compliance_management'
            )

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error viewing compliance note: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the note")
            return redirect('compliance_management:compliance_notes_list')

class ComplianceNoteDeleteView(LoginRequiredMixin, DeleteView):
    model = ComplianceNote
    success_url = reverse_lazy('compliance_management:compliance_notes_list')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            note = self.get_object()
            if not PermissionManager.check_module_modify(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied to delete compliance note for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to delete notes")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in compliance note delete dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('compliance_notes_list')

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Compliance note deleted successfully")
            return response
        except Exception as e:
            logger.error(f"Error deleting compliance note: {str(e)}")
            messages.error(request, "Failed to delete compliance note")
            return redirect('compliance_management:compliance_note_detail', pk=self.get_object().pk)

    def get_template_names(self):
        return [get_template_path(
            'compliance_note_confirm_delete.html',
            self.request.user.role,
            'compliance_management'
        )]
