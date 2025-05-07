from django.core.management.base import BaseCommand
from appointment_management.models import DoctorTimeSlot
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'List all doctor time slots in the database'

    def handle(self, *args, **kwargs):
        slots = DoctorTimeSlot.objects.select_related('doctor', 'center').order_by('date', 'start_time')
        if not slots.exists():
            self.stdout.write("No time slots found.")
            return

        for slot in slots:
            doctor_name = slot.doctor.get_full_name() if hasattr(slot.doctor, 'get_full_name') else str(slot.doctor)
            self.stdout.write(f"Doctor: {doctor_name}, Center: {slot.center.name}, Date: {slot.date}, Start: {slot.start_time}, End: {slot.end_time}, Available: {slot.is_available}")
