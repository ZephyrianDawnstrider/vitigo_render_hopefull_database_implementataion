from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from doctor_management.models import DoctorProfile, Specialization
import random
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate doctor profiles for users with Doctor role'

    def handle(self, *args, **kwargs):
        # Get all users with Doctor role
        doctor_users = User.objects.filter(role__name='DOCTOR')
        
        if not doctor_users.exists():
            self.stdout.write(self.style.WARNING('No users found with Doctor role'))
            return

        # Sample data for random selection
        experience_choices = ['0-5', '5-10', '10-15', '15+']
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'West Bengal']
        
        for user in doctor_users:
            # Skip if doctor profile already exists
            if hasattr(user, 'doctor_profile'):
                continue

            # Create doctor profile with random data
            profile = DoctorProfile.objects.create(
                user=user,
                registration_number=f"DOC{random.randint(10000, 99999)}",
                qualification=random.choice([
                    "MBBS, MD Dermatology",
                    "MBBS, DVD",
                    "MD Dermatology, DNB",
                    "MBBS, DDVL"
                ]),
                experience=random.choice(experience_choices),
                consultation_fee=Decimal(random.randint(500, 2000)),
                about=f"Experienced dermatologist specializing in vitiligo treatment with {random.randint(5, 20)} years of experience.",
                address=f"{random.randint(1, 100)}, Medical Center, {random.choice(['Main Road', 'Hospital Lane', 'Healthcare Avenue'])}",
                city=random.choice(cities),
                state=random.choice(states),
                country='India',
                rating=round(random.uniform(3.5, 5.0), 1),
                is_available=True
            )

            # Add random specializations (assuming specializations exist)
            specializations = Specialization.objects.all()
            if specializations.exists():
                profile.specializations.add(*random.sample(
                    list(specializations), 
                    k=min(3, specializations.count())
                ))

            self.stdout.write(
                self.style.SUCCESS(f'Created doctor profile for {user.get_full_name()}')
            )
