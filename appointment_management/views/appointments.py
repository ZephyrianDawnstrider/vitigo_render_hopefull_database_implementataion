# Python Standard Library imports
import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Django core imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.views.generic.edit import FormView

# Django REST Framework imports
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from doctor_management.models import DoctorProfile
from error_handling.views import handler403, handler404, handler500
from patient_management.models import MedicalHistory
from notifications.services import NotificationService
from notifications.models import NotificationType

from ..utils import get_template_path
from ..forms import AppointmentCreateForm
from ..models import (
    Appointment,
    AppointmentReminder,
    CancellationReason,
    DoctorTimeSlot,
    ReminderConfiguration,
    ReminderTemplate,
    AppointmentAcknowledgement,
    Center
)

# Logger configuration
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()

class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    context_object_name = 'appointment'

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'appointment_management'):
            messages.error(request, "You don't have permission to view appointment details")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('appointments/detail.html', self.request.user.role, 'appointment_management')]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.object
        
        # Initialize default context values
        context.update({
            'cancellation': None,
            'previous_appointments': [],
            'error_messages': []
        })

        # Get cancellation reason if appointment is cancelled
        if appointment.status == 'CANCELLED':
            try:
                context['cancellation'] = CancellationReason.objects.get(appointment=appointment)
            except CancellationReason.DoesNotExist:
                logger.warning(f"No cancellation reason found for cancelled appointment {appointment.id}")
            except Exception as e:
                logger.error(f"Error fetching cancellation reason: {str(e)}")
                context['error_messages'].append("Error loading cancellation details")

        # Get previous appointments safely
        try:
            context['previous_appointments'] = Appointment.objects.filter(
                patient=appointment.patient,
                date__lt=appointment.date
            ).order_by('-date')[:5]
        except Exception as e:
            logger.error(f"Error fetching previous appointments: {str(e)}")
            context['error_messages'].append("Error loading previous appointments")

        # Add appointment status information
        context.update({
            'can_edit': appointment.status in ['PENDING', 'CONFIRMED'],
            'can_cancel': appointment.status not in ['COMPLETED', 'CANCELLED', 'NO_SHOW'],
            'status_display': appointment.get_status_display(),
            'is_upcoming': appointment.date >= timezone.now().date()
        })
        
        return context

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except self.model.DoesNotExist:
            return handler404(self.request, exception="Appointment not found")


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentCreateForm
    success_url = reverse_lazy('appointment_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'appointment_management'):
            messages.error(request, "You don't have permission to create appointments")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('appointments/create.html', self.request.user.role, 'appointment_management')]

    def get_initial(self):
        initial = super().get_initial()
        # Set the logged-in user as the default patient
        initial['patient'] = self.request.user.pk
        return initial

    def form_valid(self, form):
        try:
            with transaction.atomic():
                appointment = form.save(commit=False)
                
                # Get the selected timeslot
                timeslot_id = form.cleaned_data.get('timeslot_id')
                if not timeslot_id:
                    messages.error(self.request, 'Time slot selection is required')
                    return self.form_invalid(form)

                try:
                    timeslot = DoctorTimeSlot.objects.get(id=timeslot_id)
                except DoctorTimeSlot.DoesNotExist:
                    messages.error(self.request, 'Selected time slot is invalid')
                    return self.form_invalid(form)

                # Additional validation for past time slots
                current_datetime = timezone.now()
                appointment_datetime = timezone.make_aware(
                    datetime.combine(appointment.date, timeslot.start_time)
                )

                if appointment_datetime < current_datetime:
                    messages.error(self.request, 'Cannot create appointments for past time slots')
                    return self.form_invalid(form)

                # Verify timeslot is still available
                if not timeslot.is_available:
                    messages.error(self.request, 'This time slot is no longer available')
                    return self.form_invalid(form)
                
                # Follow-up specific validation
                if appointment.appointment_type == 'FOLLOW_UP':
                    days_until_appointment = (appointment.date - timezone.now().date()).days
                    if days_until_appointment > 30:
                        messages.error(self.request, 'Follow-up appointments cannot be scheduled more than 30 days in advance')
                        return self.form_invalid(form)
                    if days_until_appointment < 1:
                        messages.error(self.request, 'Follow-up appointments must be scheduled at least 1 day in advance')
                        return self.form_invalid(form)

                # Set the timeslot and mark it as unavailable
                appointment.time_slot = timeslot
                timeslot.is_available = False
                timeslot.save()
                
                appointment.save()

                # Create notifications outside the transaction
                self._create_appointment_notifications(appointment)
                
                messages.success(self.request, 'Appointment created successfully!')
                return super().form_valid(form)
                
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            messages.error(self.request, 'Error creating appointment. Please try again.')
            return self.form_invalid(form)

    def _create_appointment_notifications(self, appointment):
        """
        Create notifications for both patient and doctor
        """
        try:
            # Get or create notification types
            appointment_created_type, _ = NotificationType.objects.get_or_create(
                name='APPOINTMENT_CREATED',
                defaults={'description': 'New appointment created'}
            )

            # Patient notification
            patient_message = (
                f"Your appointment with Dr. {appointment.doctor.get_full_name()} "
                f"has been scheduled for {appointment.date} at "
                f"{appointment.time_slot.start_time.strftime('%I:%M %p')}"
            )
            
            success, error = NotificationService.create_notifications(
                user=appointment.patient,
                notification_type=appointment_created_type,
                message=patient_message,
                send_email=True,
                send_sms=True,
                phone_number=appointment.patient.phone_number if hasattr(appointment.patient, 'phone_number') else None
            )

            if not success:
                logger.error(f"Failed to create patient notification: {error}")

            # Doctor notification
            doctor_message = (
                f"New appointment scheduled with {appointment.patient.get_full_name()} "
                f"for {appointment.date} at "
                f"{appointment.time_slot.start_time.strftime('%I:%M %p')}"
            )
            
            success, error = NotificationService.create_notifications(
                user=appointment.doctor,
                notification_type=appointment_created_type,
                message=doctor_message,
                send_email=True
            )

            if not success:
                logger.error(f"Failed to create doctor notification: {error}")

        except Exception as e:
            logger.error(f"Error in _create_appointment_notifications: {str(e)}")
            # Don't raise the exception - we want the appointment to be created even if notifications fail

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_timeslots(request):
    """
    Get available time slots for a doctor on a specific date at a specific center.
    Required query parameters: user_id, date, center_id
    """
    logger.info("Starting get_doctor_timeslots function")
    
    try:
        # Get and validate parameters
        user_id = request.GET.get('user_id')
        date_str = request.GET.get('date')
        center_id = request.GET.get('center_id')

        logger.debug(f"Received parameters - user_id: {user_id}, date: {date_str}, center_id: {center_id}")

        if not all([user_id, date_str, center_id]):
            missing_params = []
            if not user_id: missing_params.append('user_id')
            if not date_str: missing_params.append('date')
            if not center_id: missing_params.append('center_id')
            
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            return Response({"error": error_msg}, status=400)

        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}"
            logger.error(error_msg)
            return Response({"error": error_msg}, status=400)

        # Get doctor and validate role
        try:
            doctor = User.objects.get(id=user_id)
            if not doctor.role.name == 'DOCTOR':
                error_msg = f"User {user_id} is not a doctor"
                logger.error(error_msg)
                return Response({"error": error_msg}, status=400)
        except User.DoesNotExist:
            error_msg = f"Doctor with ID {user_id} not found"
            logger.error(error_msg)
            return Response({"error": error_msg}, status=404)

        # Get center
        try:
            center = Center.objects.get(id=center_id, is_active=True)
        except Center.DoesNotExist:
            error_msg = f"Center with ID {center_id} not found or inactive"
            logger.error(error_msg)
            return Response({"error": error_msg}, status=404)

        # Get time slots
        time_slots = DoctorTimeSlot.objects.filter(
            doctor=doctor,
            date=date,
            center=center
        ).order_by('start_time')

        logger.debug(f"Found {time_slots.count()} time slots")

        # Convert time slots to response format
        slots_data = []
        current_datetime = timezone.now()
        
        for slot in time_slots:
            slot_datetime = timezone.make_aware(datetime.combine(date, slot.start_time))
            
            if slot_datetime > current_datetime:
                slots_data.append({
                    'id': slot.id,
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'is_available': slot.is_available,
                })

        response_data = {
            'doctor_name': doctor.get_full_name(),
            'date': date_str,
            'center_name': center.name,
            'timeslots': slots_data
        }

        if not slots_data:
            logger.info("No available time slots found")
            response_data['message'] = 'No available time slots found for this date and center.'

        logger.info("Successfully retrieved time slots")
        return Response(response_data)

    except Exception as e:
        error_msg = f"Unexpected error in get_doctor_timeslots: {str(e)}"
        logger.exception(error_msg)
        return Response(
            {"error": "An unexpected error occurred while fetching time slots"}, 
            status=500
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_centers(request):
    """
    Get distinct centers (clinics) where the doctor has available time slots.
    Required query parameter: user_id (doctor id)
    """
    try:
        user_id = request.GET.get('user_id')
        if not user_id:
            return Response({"error": "user_id parameter is required"}, status=400)

        try:
            doctor = User.objects.get(id=user_id)
            if not doctor.role.name == 'DOCTOR':
                return Response({"error": "User is not a doctor"}, status=400)
        except User.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

        centers = Center.objects.filter(
            doctor_time_slots__doctor=doctor,
            is_active=True
        ).distinct().order_by('name')

        centers_data = [{"id": center.id, "name": center.name} for center in centers]

        return Response({"centers": centers_data})

    except Exception as e:
        logger.exception(f"Unexpected error in get_doctor_centers: {str(e)}")
        return Response({"error": "An unexpected error occurred"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_available_dates(request):
    """
    Get distinct available dates for a doctor at a specific center.
    Required query parameters: user_id (doctor id), center_id
    """
    try:
        user_id = request.GET.get('user_id')
        center_id = request.GET.get('center_id')

        if not user_id or not center_id:
            missing = []
            if not user_id:
                missing.append('user_id')
            if not center_id:
                missing.append('center_id')
            return Response({"error": f"Missing required parameters: {', '.join(missing)}"}, status=400)

        try:
            doctor = User.objects.get(id=user_id)
            if not doctor.role.name == 'DOCTOR':
                return Response({"error": "User is not a doctor"}, status=400)
        except User.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

        try:
            center = Center.objects.get(id=center_id, is_active=True)
        except Center.DoesNotExist:
            return Response({"error": "Center not found or inactive"}, status=404)

        # Query distinct dates where doctor has available time slots at the center
        dates_qs = DoctorTimeSlot.objects.filter(
            doctor=doctor,
            center=center,
            is_available=True,
            date__gte=timezone.now().date()
        ).values_list('date', flat=True).distinct().order_by('date')

        dates = [date.strftime('%Y-%m-%d') for date in dates_qs]

        return Response({"available_dates": dates})

    except Exception as e:
        logger.exception(f"Unexpected error in get_doctor_available_dates: {str(e)}")
        return Response({"error": "An unexpected error occurred"}, status=500)

@api_view(['PUT'])
def update_doctor_timeslot(request, timeslot_id):
    """
    Update a doctor's timeslot availability
    Required path parameter:
    - timeslot_id: ID of the timeslot to update
    Required body parameter:
    - is_available: boolean
    """
    logger.info(f"Updating doctor timeslot {timeslot_id}")
    
    try:
        # Get the timeslot
        try:
            timeslot = DoctorTimeSlot.objects.get(id=timeslot_id)
        except DoctorTimeSlot.DoesNotExist:
            logger.error(f"Timeslot with id {timeslot_id} not found")
            return Response(
                {"error": "Timeslot not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Get and validate is_available from request body
        is_available = request.data.get('is_available')
        if is_available is None:
            logger.error("No is_available value provided")
            return Response(
                {"error": "is_available is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the timeslot
        timeslot.is_available = is_available
        timeslot.save()

        # Return updated timeslot data
        response_data = {
            'id': timeslot.id,
            'doctor_name': timeslot.doctor.user.get_full_name(),
            'date': timeslot.date,
            'start_time': timeslot.start_time.strftime('%H:%M'),
            'end_time': timeslot.end_time.strftime('%H:%M'),
            'is_available': timeslot.is_available
        }

        logger.info(f"Successfully updated timeslot {timeslot_id}")
        return Response(response_data)

    except Exception as e:
        logger.exception(f"Unexpected error in update_doctor_timeslot: {str(e)}")
        return Response(
            {"error": "An unexpected error occurred"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
def update_appointment_timeslot(request, appointment_id):
    """
    Update an appointment's time slot
    Required path parameter:
    - appointment_id: ID of the appointment to update
    Required body parameter:
    - timeslot_id: ID of the new timeslot
    """
    logger.info(f"Updating appointment {appointment_id} time slot")
    
    try:
        # Get the appointment
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            logger.error(f"Appointment with id {appointment_id} not found")
            return Response(
                {"error": "Appointment not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Get and validate timeslot_id from request body
        timeslot_id = request.data.get('timeslot_id')
        if timeslot_id is None:
            logger.error("No timeslot_id provided")
            return Response(
                {"error": "timeslot_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the timeslot
        try:
            timeslot = DoctorTimeSlot.objects.get(id=timeslot_id)
        except DoctorTimeSlot.DoesNotExist:
            logger.error(f"TimeSlot with id {timeslot_id} not found")
            return Response(
                {"error": "TimeSlot not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify timeslot is available
        if not timeslot.is_available:
            logger.error(f"TimeSlot {timeslot_id} is not available")
            return Response(
                {"error": "TimeSlot is not available"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the appointment
        with transaction.atomic():
            # Make old timeslot available if it exists
            if appointment.time_slot:
                old_timeslot = appointment.time_slot
                old_timeslot.is_available = True
                old_timeslot.save()

            # Update appointment with new timeslot
            appointment.time_slot = timeslot
            appointment.save()

            # Mark new timeslot as unavailable
            timeslot.is_available = False
            timeslot.save()

        # Return updated appointment data
        response_data = {
            'id': appointment.id,
            'patient_name': appointment.patient.get_full_name(),
            'doctor_name': appointment.doctor.get_full_name(),
            'date': appointment.date,
            'timeslot': {
                'id': timeslot.id,
                'start_time': timeslot.start_time.strftime('%H:%M'),
                'end_time': timeslot.end_time.strftime('%H:%M')
            }
        }

        logger.info(f"Successfully updated appointment {appointment_id} time slot")
        return Response(response_data)

    except Exception as e:
        logger.exception(f"Unexpected error in update_appointment_timeslot: {str(e)}")
        return Response(
            {"error": "An unexpected error occurred"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def update_appointment_status(request, appointment_id):
    """Update an appointment's status"""
    logger.info(f"Starting status update for appointment {appointment_id}")
    logger.debug(f"Request data: {request.data}")
    
    try:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        new_status = request.data.get('status')
        old_status = appointment.status
        
        if not new_status:
            return Response({"error": "Status is required"}, status=400)

        # Status-specific messages
        status_messages = {
            'CONFIRMED': {
                'success': 'Appointment confirmed successfully. Patient will be notified.',
                'log': f'Appointment {appointment_id} confirmed by {request.user.get_full_name()}'
            },
            'CANCELLED': {
                'success': 'Appointment cancelled successfully. All parties will be notified.',
                'log': f'Appointment {appointment_id} cancelled by {request.user.get_full_name()}'
            },
            'COMPLETED': {
                'success': 'Appointment marked as completed successfully.',
                'log': f'Appointment {appointment_id} marked as completed by {request.user.get_full_name()}'
            },
            'NO_SHOW': {
                'success': 'Patient marked as no-show for this appointment.',
                'log': f'Appointment {appointment_id} marked as no-show by {request.user.get_full_name()}'
            }
        }

        # Handle cancellation
        if new_status == 'CANCELLED':
            reason = request.data.get('reason')
            if not reason:
                return Response({"error": "Cancellation reason is required"}, status=400)
            
            try:
                with transaction.atomic():
                    appointment.status = new_status
                    appointment.save()
                    
                    CancellationReason.objects.create(
                        appointment=appointment,
                        reason=reason,
                        cancelled_by=request.user
                    )
                    
                    if appointment.time_slot:
                        appointment.time_slot.is_available = True
                        appointment.time_slot.save()
                        logger.info(f"Released time slot for cancelled appointment {appointment_id}")

                    # Create cancellation notifications outside the transaction
                    _create_cancellation_notifications(appointment, reason, request.user)
                    
                    messages.warning(request, f"Appointment cancelled - {reason}")
                    logger.info(status_messages[new_status]['log'])
            except Exception as e:
                logger.error(f"Failed to cancel appointment: {str(e)}")
                return Response({"error": "Failed to cancel appointment"}, status=500)
        else:
            # Handle other status updates
            try:
                appointment.status = new_status
                appointment.save()
                
                # Add appropriate messages based on status
                if new_status == 'CONFIRMED':
                    messages.success(request, status_messages[new_status]['success'])
                elif new_status == 'COMPLETED':
                    messages.success(request, status_messages[new_status]['success'])
                elif new_status == 'NO_SHOW':
                    messages.warning(request, status_messages[new_status]['success'])
                
                logger.info(status_messages.get(new_status, {}).get('log', f'Status updated to {new_status}'))
            except Exception as e:
                logger.error(f"Failed to update status: {str(e)}")
                return Response({"error": "Failed to update status"}, status=500)

        # Return success response with detailed message
        return Response({
            "status": "success",
            "message": status_messages.get(new_status, {}).get('success', f'Status updated to {new_status}'),
            "appointment": {
                "id": appointment.id,
                "new_status": new_status,
                "old_status": old_status,
                "patient_name": appointment.patient.get_full_name(),
                "doctor_name": appointment.doctor.get_full_name(),
                "date": appointment.date,
                "time": appointment.time_slot.start_time if appointment.time_slot else None
            }
        })

    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return Response({"error": "An unexpected error occurred"}, status=500)

def _create_cancellation_notifications(appointment, reason, cancelled_by):
    """
    Create notifications for appointment cancellation
    """
    try:
        cancellation_type, _ = NotificationType.objects.get_or_create(
            name='APPOINTMENT_CANCELLED',
            defaults={'description': 'Appointment cancelled notification'}
        )

        # Patient notification
        patient_message = (
            f"Your appointment with Dr. {appointment.doctor.get_full_name()} "
            f"for {appointment.date} has been cancelled. Reason: {reason}"
        )
        
        NotificationService.create_notifications(
            user=appointment.patient,
            notification_type=cancellation_type,
            message=patient_message,
            send_email=True,
            send_sms=True,
            phone_number=appointment.patient.phone_number if hasattr(appointment.patient, 'phone_number') else None
        )

        # Doctor notification
        doctor_message = (
            f"Appointment with {appointment.patient.get_full_name()} "
            f"for {appointment.date} has been cancelled by {cancelled_by.get_full_name()}. "
            f"Reason: {reason}"
        )
        
        NotificationService.create_notifications(
            user=appointment.doctor,
            notification_type=cancellation_type,
            message=doctor_message,
            send_email=True
        )

    except Exception as e:
        logger.error(f"Error in _create_cancellation_notifications: {str(e)}")
        # Don't raise the exception - we want the cancellation to proceed even if notifications fail


class AppointmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_delete(self.request.user, 'appointment_management')
        
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_delete(self.request.user, 'appointment_management'):
            messages.error(request, "You don't have permission to delete appointments")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, appointment_id):
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment_number = appointment.id  # Store for message

            with transaction.atomic():
                # If there's a time slot, mark it as available again
                if appointment.time_slot:
                    appointment.time_slot.is_available = True
                    appointment.time_slot.save()
                    logger.info(f"Released time slot for appointment {appointment_id}")
                
                appointment.delete()
            
            messages.success(request, f"Appointment #{appointment_number} deleted successfully")
            return redirect('appointment_dashboard')
            
        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}")
            messages.error(request, f"Error deleting appointment: {str(e)}")
            return redirect('appointment_dashboard')
        

class AppointmentRescheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'appointment_management')

    def post(self, request, appointment_id):
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            new_timeslot_id = request.POST.get('timeslot_id')

            if not new_timeslot_id:
                messages.error(request, 'Please select a new time slot')
                return redirect('appointment_dashboard')

            try:
                new_timeslot = DoctorTimeSlot.objects.get(id=new_timeslot_id)
            except DoctorTimeSlot.DoesNotExist:
                messages.error(request, 'Selected time slot is invalid')
                return redirect('appointment_dashboard')

            if not new_timeslot.is_available:
                messages.error(request, 'Selected time slot is no longer available')
                return redirect('appointment_dashboard')

            with transaction.atomic():
                # Make the old timeslot available
                if appointment.time_slot:
                    old_timeslot = appointment.time_slot
                    old_timeslot.is_available = True
                    old_timeslot.save()

                # Update appointment with new timeslot
                appointment.time_slot = new_timeslot
                appointment.date = new_timeslot.date
                appointment.save()

                # Mark new timeslot as unavailable
                new_timeslot.is_available = False
                new_timeslot.save()

            messages.success(request, 'Appointment rescheduled successfully')
            return redirect('appointment_dashboard')

        except Exception as e:
            logger.error(f"Error rescheduling appointment: {str(e)}")
            messages.error(request, 'Error rescheduling appointment')
            return redirect('appointment_dashboard')


@api_view(['POST'])
def acknowledge_appointment(request, appointment_id):
    """Handle appointment acknowledgement from both patient and staff"""
    try:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Check if user has already acknowledged
        if appointment.acknowledgements.filter(user=request.user).exists():
            messages.error(request, "You have already acknowledged this appointment")
            return redirect('appointment_detail', pk=appointment_id)

        is_patient = request.user.role.name == 'PATIENT'
        
        # Verify user permission to acknowledge
        if is_patient and request.user != appointment.patient:
            messages.error(request, "You can only acknowledge your own appointments")
            return redirect('appointment_detail', pk=appointment_id)

        # Create acknowledgement
        notes = request.POST.get('notes', '')
        acknowledgement = AppointmentAcknowledgement.objects.create(
            appointment=appointment,
            user=request.user,
            notes=notes
        )

        # Check acknowledgement status and set appropriate message
        patient_ack = appointment.acknowledgements.filter(user__role__name='PATIENT').exists()
        staff_ack = appointment.acknowledgements.filter(~Q(user__role__name='PATIENT')).exists()

        if patient_ack and staff_ack:
            messages.success(request, "Appointment fully acknowledged and confirmed")
        else:
            acknowledger_type = "Patient" if is_patient else "Staff"
            waiting_for = "staff" if is_patient else "patient"
            messages.success(
                request, 
                f"{acknowledger_type} acknowledgement recorded. Waiting for {waiting_for} acknowledgement."
            )
            
        return redirect('appointment_detail', pk=appointment_id)

    except Exception as e:
        logger.error(f"Error acknowledging appointment: {str(e)}")
        messages.error(request, "Error acknowledging appointment")
        return redirect('appointment_detail', pk=appointment_id)