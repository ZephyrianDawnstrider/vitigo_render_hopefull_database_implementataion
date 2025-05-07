# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView
from django.views import View

# Python standard library imports
from datetime import timedelta
import logging

# Local application imports
from .models import (
    Prescription, PrescriptionTemplate, TemplateItem, 
    PrescriptionItem, Consultation
)
from .utils import get_template_path
from access_control.permissions import PermissionManager
from pharmacy_management.models import Medication
from stock_management.models import StockItem

# Initialize logger
logger = logging.getLogger(__name__)

class PrescriptionDashboardView(LoginRequiredMixin, ListView):
    model = Prescription
    context_object_name = 'prescriptions'
    paginate_by = 10

    def get_template_names(self):
        return [get_template_path('prescription_dashboard.html', self.request.user.role)]

    def get_queryset(self):
        queryset = Prescription.objects.select_related(
            'consultation__patient', 
            'consultation__doctor'
        ).prefetch_related('items__medication')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(consultation__patient__first_name__icontains=search) |
                Q(consultation__patient__last_name__icontains=search) |
                Q(items__medication__name__icontains=search)
            ).distinct()
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()
        last_month = today - timedelta(days=30)
        
        # Get templates
        templates = PrescriptionTemplate.objects.filter(
            Q(doctor=self.request.user) | Q(is_global=True)
        )
        
        # Analytics data
        context.update({
            'templates': templates,
            'total_templates': templates.count(),
            'active_templates': templates.filter(is_active=True).count(),
            'total_prescriptions': Prescription.objects.count(),
            'recent_prescriptions': Prescription.objects.filter(
                created_at__gte=today - timedelta(days=7)
            ).count()
        })
        
        # Add medications list for template creation
        context['medications'] = Medication.objects.filter(is_active=True)
        
        return context

class PrescriptionTemplateCreateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to create prescription templates")
                return redirect('prescription_dashboard')

            # Extract basic information
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'
            is_global = request.POST.get('is_global') == 'on'

            # Validate required fields
            if not name:
                messages.error(request, "Template name is required")
                return redirect('prescription_dashboard')

            # Create the template
            with transaction.atomic():
                template = PrescriptionTemplate.objects.create(
                    name=name,
                    description=description,
                    doctor=request.user,
                    is_active=is_active,
                    is_global=is_global
                )

                # Process medications
                medications = request.POST.getlist('medications[]')
                dosages = request.POST.getlist('dosages[]')
                frequencies = request.POST.getlist('frequencies[]')
                durations = request.POST.getlist('durations[]')

                # Create template items
                for i in range(len(medications)):
                    if medications[i]:  # Only create if medication is selected
                        TemplateItem.objects.create(
                            template=template,
                            medication_id=medications[i],
                            dosage=dosages[i],
                            frequency=frequencies[i],
                            duration=durations[i],
                            order=i
                        )

            messages.success(request, "Prescription template created successfully")
            logger.info(f"Prescription template '{name}' created by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error creating prescription template: {str(e)}")
            messages.error(request, "An error occurred while creating the template")

        return redirect('prescription_dashboard')


class PrescriptionTemplateEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            template = get_object_or_404(PrescriptionTemplate, pk=pk)
            data = {
                'template': {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'is_active': template.is_active,
                    'is_global': template.is_global,
                    'items': list(template.items.values(
                        'id',
                        'medication_id',
                        'dosage',
                        'frequency',
                        'duration',
                        'order'
                    ))
                }
            }
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error fetching template data: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)

    def post(self, request, pk):
        try:
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                return JsonResponse({
                    'error': "You don't have permission to modify prescription templates"
                }, status=403)

            template = get_object_or_404(PrescriptionTemplate, pk=pk)

            with transaction.atomic():
                # Update basic information
                template.name = request.POST.get('name')
                template.description = request.POST.get('description', '')
                template.is_active = request.POST.get('is_active') == 'on'
                template.is_global = request.POST.get('is_global') == 'on'
                template.save()

                # Delete existing items
                template.items.all().delete()

                # Add new items
                medications = request.POST.getlist('medications[]')
                dosages = request.POST.getlist('dosages[]')
                frequencies = request.POST.getlist('frequencies[]')
                durations = request.POST.getlist('durations[]')

                for i in range(len(medications)):
                    if medications[i]:
                        TemplateItem.objects.create(
                            template=template,
                            medication_id=medications[i],
                            dosage=dosages[i],
                            frequency=frequencies[i],
                            duration=durations[i],
                            order=i
                        )

            messages.success(request, "Prescription template updated successfully")
            return redirect('prescription_dashboard')

        except Exception as e:
            logger.error(f"Error updating prescription template: {str(e)}")
            messages.error(request, "An error occurred while updating the template")
            return redirect('prescription_dashboard')

class PrescriptionTemplateDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            if not PermissionManager.check_module_delete(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to delete prescription templates")
                return redirect('prescription_dashboard')

            template = get_object_or_404(PrescriptionTemplate, pk=pk)
            
            # Additional validation if needed (e.g., only owner can delete)
            if not template.is_global and template.doctor != request.user:
                messages.error(request, "You can only delete your own templates")
                return redirect('prescription_dashboard')

            template_name = template.name
            template.delete()
            
            messages.success(request, f"Template '{template_name}' deleted successfully")
            logger.info(f"Prescription template {pk} deleted by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error deleting prescription template: {str(e)}")
            messages.error(request, "An error occurred while deleting the template")
            
        return redirect('prescription_dashboard')


class PrescriptionCreateView(LoginRequiredMixin, View):
    def post(self, request, consultation_id):
        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to create prescriptions")
                return redirect('consultation_detail', pk=consultation_id)

            with transaction.atomic():
                # Create prescription
                prescription = Prescription.objects.create(
                    consultation=consultation,
                    notes=request.POST.get('notes', '')
                )

                # Process medication items
                medications = request.POST.getlist('medications[]')
                dosages = request.POST.getlist('dosages[]')
                frequencies = request.POST.getlist('frequencies[]')
                durations = request.POST.getlist('durations[]')

                for i in range(len(medications)):
                    if medications[i]:  # Only create if medication is selected
                        medication_id = medications[i]
                        
                        # Find stock item for this medication, if available
                        stock_item = None
                        try:
                            stock_item = StockItem.objects.filter(
                                name=Medication.objects.get(id=medication_id).name,
                                current_quantity__gt=0
                            ).first()
                        except Exception as e:
                            logger.warning(f"Could not find stock item for medication {medication_id}: {str(e)}")

                        PrescriptionItem.objects.create(
                            prescription=prescription,
                            medication_id=medication_id,
                            stock_item=stock_item,  # Can be None if not in stock
                            dosage=dosages[i],
                            frequency=frequencies[i],
                            duration=durations[i],
                            quantity_prescribed=1,  # Default value
                            order=i
                        )

                messages.success(request, "Prescription created successfully")
                logger.info(f"Prescription created for consultation {consultation_id} by user {request.user.id}")

            return redirect('consultation_detail', pk=consultation_id)

        except Exception as e:
            logger.error(f"Error creating prescription: {str(e)}")
            messages.error(request, "An error occurred while creating the prescription")
            return redirect('consultation_detail', pk=consultation_id)

class UsePrescriptionTemplateView(LoginRequiredMixin, View):
    def post(self, request, consultation_id, template_id):
        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            template = get_object_or_404(PrescriptionTemplate, id=template_id)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to create prescriptions")
                return redirect('consultation_detail', pk=consultation_id)

            with transaction.atomic():
                # Create prescription from template
                prescription = Prescription.objects.create(
                    consultation=consultation,
                    template_used=template,
                    notes=f"Created from template: {template.name}"
                )

                # Create prescription items from template items
                for template_item in template.items.all():
                    # Check if medication is in stock (optional)
                    stock_item = None
                    try:
                        stock_item = StockItem.objects.filter(
                            name=template_item.medication.name,
                            current_quantity__gt=0
                        ).first()
                    except Exception as e:
                        logger.warning(f"Could not find stock item for medication {template_item.medication.id}: {str(e)}")

                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication=template_item.medication,
                        stock_item=stock_item,
                        dosage=template_item.dosage,
                        frequency=template_item.frequency,
                        duration=template_item.duration,
                        instructions=template_item.instructions,
                        quantity_prescribed=1,
                        order=template_item.order
                    )

                messages.success(request, f"Prescription created from template '{template.name}'")
                logger.info(f"Prescription created from template {template.id} for consultation {consultation_id}")

            return redirect('consultation_detail', pk=consultation_id)

        except Exception as e:
            logger.error(f"Error creating prescription from template: {str(e)}")
            messages.error(request, "An error occurred while creating the prescription")
            return redirect('consultation_detail', pk=consultation_id)

class PrescriptionEditView(LoginRequiredMixin, View):
    def get(self, request, consultation_id, prescription_id):
        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            prescription = get_object_or_404(Prescription, id=prescription_id, consultation=consultation)
            
            data = {
                'prescription': {
                    'id': prescription.id,
                    'notes': prescription.notes,
                    'items': list(prescription.items.values(
                        'id',
                        'medication_id',
                        'dosage',
                        'frequency',
                        'duration',
                        'instructions',
                        'quantity_prescribed',
                        'order'
                    ))
                }
            }
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error fetching prescription data: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)

    def post(self, request, consultation_id, prescription_id):
        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            prescription = get_object_or_404(Prescription, id=prescription_id, consultation=consultation)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to edit prescriptions")
                return redirect('consultation_detail', pk=consultation_id)

            with transaction.atomic():
                # Update prescription notes
                prescription.notes = request.POST.get('notes', '')
                prescription.save()

                # Delete existing items and create new ones
                prescription.items.all().delete()

                # Process medication items
                medications = request.POST.getlist('medications[]')
                dosages = request.POST.getlist('dosages[]')
                frequencies = request.POST.getlist('frequencies[]')
                durations = request.POST.getlist('durations[]')

                for i in range(len(medications)):
                    if medications[i]:
                        medication_id = medications[i]
                        
                        # Find stock item for this medication, if available
                        stock_item = None
                        try:
                            stock_item = StockItem.objects.filter(
                                name=Medication.objects.get(id=medication_id).name,
                                current_quantity__gt=0
                            ).first()
                        except Exception as e:
                            logger.warning(f"Could not find stock item for medication {medication_id}: {str(e)}")

                        PrescriptionItem.objects.create(
                            prescription=prescription,
                            medication_id=medication_id,
                            stock_item=stock_item,
                            dosage=dosages[i],
                            frequency=frequencies[i],
                            duration=durations[i],
                            quantity_prescribed=1,
                            order=i
                        )

                messages.success(request, "Prescription updated successfully")
                logger.info(f"Prescription {prescription_id} updated for consultation {consultation_id}")

            return redirect('consultation_detail', pk=consultation_id)

        except Exception as e:
            logger.error(f"Error updating prescription: {str(e)}")
            messages.error(request, "An error occurred while updating the prescription")
            return redirect('consultation_detail', pk=consultation_id)

