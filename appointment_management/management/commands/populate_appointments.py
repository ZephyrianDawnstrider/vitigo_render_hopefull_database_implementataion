from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.core.management import call_command
from datetime import timedelta
from appointment_management.models import (
    Appointment,
    DoctorTimeSlot,
    TimeSlotConfig,
    ReminderTemplate,
    ReminderConfiguration,
    AppointmentReminder,
    CancellationReason,
    AppointmentAcknowledgement,
    Center
)
from access_control.models import Role
import random
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Delete existing appointments and related data, then create new sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of appointments to create'
        )
        parser.add_argument(
            '--keep-existing',
            action='store_true',
            help='Keep existing appointments instead of deleting them'
        )

    def handle(self, *args, **kwargs):
        count = kwargs['count']
        keep_existing = kwargs['keep_existing']

        try:
            with transaction.atomic():
                # Always run populate_timeslots first to ensure clean data
                self.stdout.write("Running populate_timeslots command first...")
                call_command('populate_timeslots')

                # Create configurations
                self.create_timeslot_configs()
                self.create_reminder_templates()
                self.create_reminder_configurations()

                # Get roles and users
                try:
                    patient_role = Role.objects.get(name='PATIENT')
                    doctor_role = Role.objects.get(name='DOCTOR')
                    patients = User.objects.filter(role=patient_role, is_active=True)
                    doctors = User.objects.filter(role=doctor_role, is_active=True)
                except Role.DoesNotExist:
                    self.stdout.write(self.style.ERROR('Required roles not found'))
                    return

                if not patients.exists() or not doctors.exists():
                    self.stdout.write(self.style.ERROR('No active patients or doctors found'))
                    return

                # Create appointments with diverse data using existing timeslots
                self.create_diverse_appointments(count, doctors, patients)

        except Exception as e:
            logger.error(f'Failed to populate appointments: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Failed to populate appointments: {str(e)}'))

    def create_timeslot_configs(self):
        """Create standard time slot configurations"""
        slots = [
            {'start': '09:00', 'end': '12:00', 'duration': 30},
            {'start': '14:00', 'end': '17:00', 'duration': 45},
            {'start': '18:00', 'end': '21:00', 'duration': 60}
        ]
        for slot in slots:
            TimeSlotConfig.objects.create(
                start_time=slot['start'],
                end_time=slot['end'],
                duration=slot['duration']
            )
        self.stdout.write(self.style.SUCCESS('Created time slot configurations'))

    def create_reminder_templates(self):
        """Create reminder templates"""
        templates = [
            {
                'name': '24h Reminder',
                'days_before': 1,
                'hours_before': 0,
                'message_template': 'Hello {patient}, reminder for your appointment with {doctor} tomorrow at {time}.'
            },
            {
                'name': 'Same Day Reminder',
                'days_before': 0,
                'hours_before': 4,
                'message_template': 'Your appointment with {doctor} is in 4 hours at {time}.'
            },
            {
                'name': 'Week Before Reminder',
                'days_before': 7,
                'hours_before': 0,
                'message_template': 'You have an upcoming appointment with {doctor} on {date} at {time}.'
            }
        ]
        for template in templates:
            ReminderTemplate.objects.create(**template)
        self.stdout.write(self.style.SUCCESS('Created reminder templates'))

    def create_reminder_configurations(self):
        """Create reminder configurations for each appointment type"""
        templates = ReminderTemplate.objects.all()
        for apt_type in Appointment.APPOINTMENT_TYPES:
            config = ReminderConfiguration.objects.create(
                appointment_type=apt_type[0],
                reminder_types={
                    'email': True,
                    'sms': True if apt_type[0] in ['PROCEDURE', 'PHOTOTHERAPY'] else False
                }
            )
            config.templates.set(templates)
        self.stdout.write(self.style.SUCCESS('Created reminder configurations'))

    def create_diverse_appointments(self, count, doctors, patients):
        """Create appointments with diverse types, statuses, and priorities"""
        appointment_types = [choice[0] for choice in Appointment.APPOINTMENT_TYPES]
        statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
        priorities = [choice[0] for choice in Appointment.PRIORITY_CHOICES]
        
        appointments_created = 0
        cancelled_count = 0
        acknowledged_count = 0

        # Get all centers
        centers = list(Center.objects.filter(is_active=True))
        if not centers:
            self.stdout.write(self.style.ERROR('No active centers found'))
            return

        # Get all available timeslots
        available_timeslots = list(DoctorTimeSlot.objects.filter(
            is_available=True,
            center__in=centers
        ))
        
        if not available_timeslots:
            self.stdout.write(self.style.ERROR('No available timeslots found'))
            return

        for _ in range(count):
            try:
                # Randomly select a timeslot and its associated doctor and center
                timeslot = random.choice(available_timeslots)
                doctor = timeslot.doctor
                center = timeslot.center
                patient = random.choice(patients)
                
                # Remove used timeslot from available list
                available_timeslots.remove(timeslot)

                # Generate random appointment data
                apt_type = random.choice(appointment_types)
                status = random.choice(statuses)
                priority = random.choice(priorities)

                # Create appointment with center
                appointment = Appointment.objects.create(
                    patient=patient,
                    doctor=doctor,
                    center=center,  # Add center to appointment
                    appointment_type=apt_type,
                    date=timeslot.date,
                    time_slot=timeslot,
                    status=status,
                    priority=priority,
                    notes=f'Sample {apt_type} appointment at {center.name}'
                )

                # Mark timeslot as unavailable
                timeslot.is_available = False
                timeslot.save()

                # Create cancellation reason for some cancelled appointments
                if status == 'CANCELLED' and cancelled_count < count // 4:
                    CancellationReason.objects.create(
                        appointment=appointment,
                        reason=random.choice([
                            'Patient request',
                            'Doctor unavailable',
                            'Emergency',
                            'Scheduling conflict',
                            'Weather conditions',
                            'Transportation issues',
                            'Family emergency',
                            'Medical emergency'
                        ]),
                        cancelled_by=random.choice([patient, doctor])
                    )
                    cancelled_count += 1

                # Create acknowledgements for some confirmed appointments
                if status == 'CONFIRMED' and acknowledged_count < count // 3:
                    AppointmentAcknowledgement.objects.create(
                        appointment=appointment,
                        user=patient,
                        notes=random.choice([
                            'Patient confirmed attendance',
                            'Will arrive on time',
                            'Acknowledge appointment details',
                            'Confirmed via mobile app'
                        ])
                    )
                    AppointmentAcknowledgement.objects.create(
                        appointment=appointment,
                        user=doctor,
                        notes=random.choice([
                            'Doctor confirmed availability',
                            'Scheduled in calendar',
                            'Reviewed patient history',
                            'Ready for appointment'
                        ])
                    )
                    acknowledged_count += 1

                appointments_created += 1

                if not available_timeslots:
                    self.stdout.write(self.style.WARNING('Ran out of available timeslots'))
                    break

            except Exception as e:
                logger.error(f'Failed to create appointment: {str(e)}')
                self.stdout.write(self.style.WARNING(f'Failed to create appointment: {str(e)}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {appointments_created} appointments\n'
                f'Including {cancelled_count} cancelled appointments and '
                f'{acknowledged_count} acknowledged appointments'
            )
        )