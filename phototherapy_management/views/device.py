# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.generic import View
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView
from django.core.exceptions import ValidationError

# Local/application imports
from error_handling.views import handler500
from phototherapy_management.models import DeviceMaintenance, PhototherapyDevice
from phototherapy_management.utils import get_template_path
from phototherapy_management.forms import PhototherapyDeviceForm, ScheduleMaintenanceForm

# Configure logger  
logger = logging.getLogger(__name__)

# Get user model
User = get_user_model()

class DeviceManagementView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Fetch devices with related data
            devices = PhototherapyDevice.objects.select_related(
                'phototherapy_type'
            ).prefetch_related(
                'maintenance_records'
            ).order_by('-is_active', 'name')

            # Calculate maintenance statistics
            maintenance_needed = devices.filter(
                next_maintenance_date__lte=timezone.now().date()
            ).count()

            maintenance_records = DeviceMaintenance.objects.select_related(
                'device'
            ).order_by('-maintenance_date')[:5]  # Get 5 most recent records

            # Group devices by type
            devices_by_type = {}
            for device in devices:
                type_name = device.phototherapy_type.name
                if type_name not in devices_by_type:
                    devices_by_type[type_name] = []
                devices_by_type[type_name].append(device)

            context = {
                'devices': devices,
                'devices_by_type': devices_by_type,
                'total_devices': devices.count(),
                'active_devices': devices.filter(is_active=True).count(),
                'maintenance_needed': maintenance_needed,
                'recent_maintenance': maintenance_records,
            }

            template_path = get_template_path('device_management.html', request.user.role, 'phototherapy_management')
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in device management view: {str(e)}")
            messages.error(request, "An error occurred while loading device data")
            return handler500(request, exception=str(e))
        

class RegisterDeviceView(LoginRequiredMixin, CreateView):
    form_class = PhototherapyDeviceForm
    template_name_suffix = '_register'
    success_url = reverse_lazy('device_management')

    def get_template_names(self):
        return [get_template_path('device_register.html', self.request.user.role, 'phototherapy_management')]

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Device registered successfully")
            return response
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            messages.error(self.request, "An error occurred while registering the device")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below")
        return super().form_invalid(form)
    

class ScheduleMaintenanceView(LoginRequiredMixin, CreateView):
    form_class = ScheduleMaintenanceForm
    template_name_suffix = '_schedule'
    success_url = reverse_lazy('device_management')

    def get_template_names(self):
        return [get_template_path('device_maintenance_schedule.html', self.request.user.role, 'phototherapy_management')]

    def form_valid(self, form):
        try:
            # Set the created_by field
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            
            # Update the device's maintenance dates
            device = form.instance.device
            device.last_maintenance_date = form.instance.maintenance_date
            device.next_maintenance_date = form.instance.next_maintenance_due
            device.save()

            messages.success(self.request, "Maintenance scheduled successfully")
            return response
        except Exception as e:
            logger.error(f"Error scheduling maintenance: {str(e)}")
            messages.error(self.request, "An error occurred while scheduling maintenance")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below")
        return super().form_invalid(form)

class EditDeviceView(LoginRequiredMixin, View):
    def post(self, request, device_id):
        try:
            device = PhototherapyDevice.objects.get(id=device_id)
            
            # Update device fields
            device.name = request.POST.get('name')
            device.model_number = request.POST.get('model_number')
            device.serial_number = request.POST.get('serial_number')
            device.location = request.POST.get('location')
            device.next_maintenance_date = request.POST.get('next_maintenance_date')
            device.is_active = request.POST.get('is_active') == 'True'
            device.maintenance_notes = request.POST.get('maintenance_notes')
            
            # Validate and save
            device.full_clean()
            device.save()
            
            messages.success(request, "Device updated successfully")
        except PhototherapyDevice.DoesNotExist:
            messages.error(request, "Device not found")
        except ValidationError as e:
            messages.error(request, f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Error updating device: {str(e)}")
            messages.error(request, "An error occurred while updating the device")
            
        return redirect('device_management')

class DeleteDeviceView(LoginRequiredMixin, DeleteView):
    model = PhototherapyDevice
    success_url = reverse_lazy('device_management')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            device = self.get_object()
            # Check if device has associated sessions before deletion
            if device.phototherapysession_set.exists():
                messages.error(request, 'Cannot delete device with associated sessions')
                return redirect('device_management')
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in delete device dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('device_management')
    
    def post(self, request, *args, **kwargs):
        try:
            device = self.get_object()
            device_name = device.name
            response = super().post(request, *args, **kwargs)
            messages.success(request, f'Successfully deleted device: {device_name}')
            return response
        except Exception as e:
            logger.error(f"Error deleting device: {str(e)}")
            messages.error(request, 'Failed to delete device')
            return redirect('device_management')