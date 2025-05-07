from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from calendar import monthrange
from ..models import DoctorTimeSlot, Center
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403
from ..utils import get_template_path
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class AppointmentCalendarView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'appointment_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to view the appointment calendar")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path(
            'calendar/slot_calendar.html',
            self.request.user.role,
            'appointment_management'
        )]

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            
            # Get current year and month from query parameters or use current date
            year = int(self.request.GET.get('year', timezone.now().year))
            month = int(self.request.GET.get('month', timezone.now().month))
            
            # Get filter parameters - change None to empty string
            doctor_id = self.request.GET.get('doctor', '')
            center_id = self.request.GET.get('center', '')
            availability = self.request.GET.get('availability', '')
            
            # Get first and last day of month
            _, last_day = monthrange(year, month)
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, last_day).date()
            
            # Base queryset with efficient joins
            slots = DoctorTimeSlot.objects.select_related(
                'doctor', 'center'
            ).filter(
                date__range=[start_date, end_date]
            )

            # Apply filters only if they have values
            if doctor_id and doctor_id != 'None':
                slots = slots.filter(doctor_id=doctor_id)
            if center_id and center_id != 'None':
                slots = slots.filter(center_id=center_id)
            if availability and availability != 'None':
                is_available = availability == 'available'
                slots = slots.filter(is_available=is_available)

            # Organize slots by date
            calendar_data = {}
            current_date = start_date
            while current_date <= end_date:
                calendar_data[current_date] = []
                day_slots = slots.filter(date=current_date)
                for slot in day_slots:
                    calendar_data[current_date].append({
                        'id': slot.id,
                        'doctor_name': slot.doctor.get_full_name(),
                        'center_name': slot.center.name,
                        'start_time': slot.start_time,
                        'end_time': slot.end_time,
                        'is_available': slot.is_available,
                    })
                current_date += timedelta(days=1)

            # Get all active doctors and centers for filters
            doctors = User.objects.filter(
                role__name='DOCTOR',
                is_active=True
            ).order_by('first_name')
            
            centers = Center.objects.filter(
                is_active=True
            ).order_by('name')

            context.update({
                'calendar_data': calendar_data,
                'year': year,
                'month': month,
                'month_name': datetime(year, month, 1).strftime('%B'),
                'prev_month': (datetime(year, month, 1) - timedelta(days=1)).strftime('%Y-%m'),
                'next_month': (datetime(year, month, last_day) + timedelta(days=1)).strftime('%Y-%m'),
                'doctors': doctors,
                'centers': centers,
                'selected_doctor': doctor_id if doctor_id and doctor_id != 'None' else '',
                'selected_center': center_id if center_id and center_id != 'None' else '',
                'selected_availability': availability if availability and availability != 'None' else '',
                'page_title': 'Appointment Calendar',
                'page_description': 'View and manage appointment slots across all centers'
            })
            
            return context
            
        except Exception as e:
            logger.error(f"Error in calendar view: {str(e)}")
            messages.error(self.request, "Error loading calendar data")
            return {
                'calendar_data': {},
                'error': True,
                'error_message': 'Unable to load calendar data'
            }
