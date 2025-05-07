# appointment_management/management/commands/populate_timeslots.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction
from access_control.models import Role
from appointment_management.models import (
    Center, DoctorTimeSlot, Appointment, AppointmentAcknowledgement, 
    AppointmentReminder, CancellationReason, TimeSlotConfig, 
    ReminderTemplate, ReminderConfiguration
)
from doctor_management.models import DoctorAvailability
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate time slots for doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=100,
            help='Number of days to generate slots for (default: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing time slots before creating new ones'
        )

    def create_centers(self):
        """Create sample centers if they don't exist"""
        centers_data = [
            {
                'name': 'Main Clinic',
                'address': '123 Main Street, City',
                'contact_number': '123-456-7890'
            },
            {
                'name': 'North Branch',
                'address': '456 North Ave, City',
                'contact_number': '123-456-7891'
            },
            {
                'name': 'South Center',
                'address': '789 South Blvd, City',
                'contact_number': '123-456-7892'
            }
        ]
        
        centers = []
        for data in centers_data:
            center, created = Center.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            centers.append(center)
            if created:
                self.stdout.write(f'Created center: {center.name}')
        return centers

    def setup_doctor_availability(self, doctor):
        """Setup availability for a doctor for all weekdays"""
        # Clear existing availability for the doctor
        DoctorAvailability.objects.filter(doctor=doctor).delete()
        
        availability_data = []
        for day in range(5):  # Monday to Friday
            for shift, times in [
                ('MORNING', ('09:00', '12:00')),
                ('EVENING', ('14:00', '17:00'))
            ]:
                start, end = times
                availability_data.append(
                    DoctorAvailability(
                        doctor=doctor,
                        day_of_week=day,
                        shift=shift,
                        start_time=datetime.strptime(start, '%H:%M').time(),
                        end_time=datetime.strptime(end, '%H:%M').time(),
                        is_available=True
                    )
                )
        
        DoctorAvailability.objects.bulk_create(availability_data)

    def cleanup_all_data(self):
        """Clean up all related data"""
        self.stdout.write('Cleaning up all existing data...')
        models_to_clean = [
            AppointmentAcknowledgement,
            AppointmentReminder,
            CancellationReason,
            Appointment,
            DoctorTimeSlot,
            DoctorAvailability,
            TimeSlotConfig,
            ReminderTemplate,
            ReminderConfiguration,
            Center
        ]
        
        for model in models_to_clean:
            count = model.objects.all().delete()[0]
            self.stdout.write(f'Deleted {count} {model.__name__} records')

    def handle(self, *args, **options):
        days = options['days']
        clear = options['clear']

        try:
            with transaction.atomic():
                # Always clean up data regardless of --clear flag
                self.cleanup_all_data()

                # Create centers first
                centers = self.create_centers()
                if not centers:
                    self.stdout.write(self.style.ERROR('No centers available'))
                    return

                # Get doctor role and doctors
                try:
                    doctor_role = Role.objects.get(name='DOCTOR')
                    doctors = User.objects.filter(role=doctor_role, is_active=True)
                    
                    if not doctors.exists():
                        self.stdout.write(self.style.ERROR('No active doctors found'))
                        return
                        
                    self.stdout.write(f'Found {doctors.count()} active doctors')
                except Role.DoesNotExist:
                    self.stdout.write(self.style.ERROR('Doctor role not found'))
                    return

                # Setup availability for all doctors first
                for doctor in doctors:
                    self.setup_doctor_availability(doctor)
                    self.stdout.write(f'Setup availability for doctor: {doctor.email}')

                # Standard clinic hours
                time_slots = [
                    ('09:00', '09:30'), ('09:30', '10:00'),
                    ('10:00', '10:30'), ('10:30', '11:00'),
                    ('11:00', '11:30'), ('11:30', '12:00'),
                    ('14:00', '14:30'), ('14:30', '15:00'),
                    ('15:00', '15:30'), ('15:30', '16:00'),
                    ('16:00', '16:30'), ('16:30', '17:00'),
                ]

                slots_created = 0
                slots_skipped = 0
                start_date = timezone.now().date()

                for doctor in doctors:
                    self.stdout.write(f'Processing slots for doctor: {doctor.email}')
                    time_slot_data = []
                    
                    for day in range(days):
                        current_date = start_date + timedelta(days=day)
                        
                        # Skip weekends
                        if current_date.weekday() >= 5:
                            continue

                        # Randomly assign center for this day's slots
                        center = random.choice(centers)

                        # Check doctor's availability for this day
                        day_availability = doctor.availability.filter(
                            day_of_week=current_date.weekday(),
                            is_available=True
                        )
                        
                        if not day_availability.exists():
                            continue

                        # Get existing slots for this date to avoid duplicates
                        existing_slots = set(DoctorTimeSlot.objects.filter(
                            doctor=doctor,
                            date=current_date
                        ).values_list('start_time', 'end_time'))

                        # Randomly make some slots unavailable to simulate booked appointments
                        available_slots = random.sample(time_slots, k=random.randint(6, len(time_slots)))
                        
                        for start_time, end_time in time_slots:
                            start = datetime.strptime(start_time, '%H:%M').time()
                            end = datetime.strptime(end_time, '%H:%M').time()
                            
                            # Skip if slot already exists
                            if (start, end) in existing_slots:
                                slots_skipped += 1
                                continue

                            # Check if slot falls within doctor's availability
                            slot_available = any(
                                avail.start_time <= start and avail.end_time >= end 
                                for avail in day_availability
                            )
                            
                            if slot_available:
                                is_available = (start_time, end_time) in available_slots
                                time_slot_data.append(
                                    DoctorTimeSlot(
                                        doctor=doctor,
                                        center=center,  # Add center to time slot
                                        date=current_date,
                                        start_time=start,
                                        end_time=end,
                                        is_available=is_available
                                    )
                                )

                    if time_slot_data:
                        # Bulk create time slots for the doctor
                        created_slots = DoctorTimeSlot.objects.bulk_create(
                            time_slot_data,
                            ignore_conflicts=True
                        )
                        slots_created += len(created_slots)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created {slots_created} time slots (skipped {slots_skipped}) for {doctors.count()} doctors'
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))