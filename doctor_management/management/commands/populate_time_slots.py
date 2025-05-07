import random
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from appointment_management.models import DoctorTimeSlot, Center
from django.utils.timezone import make_aware

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate time slots for all doctors for the next two months with random dates and times, 5 days a week.'

    def handle(self, *args, **kwargs):
        # Define working days (Monday=0 to Friday=4)
        working_days = set(range(0, 5))
        # Define working hours range (9 AM to 5 PM)
        work_start_hour = 9
        work_end_hour = 17
        # Duration of each time slot in minutes
        slot_duration_minutes = 60

        today = datetime.now().date()
        end_date = today + timedelta(days=60)

        doctors = User.objects.filter(role__name='DOCTOR')
        centers = list(Center.objects.filter(is_active=True))
        if not centers:
            self.stdout.write(self.style.ERROR('No active centers found. Please add centers before running this command.'))
            return

        total_slots_created = 0

        for doctor in doctors:
            # Assign a center randomly for the doctor (or you can customize this logic)
            center = random.choice(centers)

            current_date = today
            while current_date <= end_date:
                if current_date.weekday() in working_days:
                    # Generate random start times within working hours for the day
                    # For simplicity, create 1-3 slots per day randomly
                    num_slots = random.randint(1, 3)
                    available_start_hours = list(range(work_start_hour, work_end_hour - slot_duration_minutes // 60 + 1))
                    random.shuffle(available_start_hours)

                    for i in range(num_slots):
                        if i >= len(available_start_hours):
                            break
                        start_hour = available_start_hours[i]
                        start_time = time(start_hour, 0)
                        end_time = (datetime.combine(current_date, start_time) + timedelta(minutes=slot_duration_minutes)).time()

                        # Check if slot already exists
                        exists = DoctorTimeSlot.objects.filter(
                            doctor=doctor,
                            center=center,
                            date=current_date,
                            start_time=start_time
                        ).exists()
                        if not exists:
                            DoctorTimeSlot.objects.create(
                                doctor=doctor,
                                center=center,
                                date=current_date,
                                start_time=start_time,
                                end_time=end_time,
                                is_available=True
                            )
                            total_slots_created += 1
                current_date += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f'Successfully created {total_slots_created} time slots for doctors.'))
