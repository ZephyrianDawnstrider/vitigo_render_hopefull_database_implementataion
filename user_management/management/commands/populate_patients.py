# File: user_management/management/commands/populate_sample_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from patient_management.models import Patient
from subscription_management.models import Subscription, SubscriptionTier

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with sample user, patient, and subscription data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')

        # Create subscription tiers
        free_tier, _ = SubscriptionTier.objects.get_or_create(
            name='Free',
            defaults={
                'description': 'Basic features for free users',
                'price': 0,
                'duration_days': 365,
                'max_patients': 1
            }
        )

        prime_tier, _ = SubscriptionTier.objects.get_or_create(
            name='Prime',
            defaults={
                'description': 'Enhanced features for prime users',
                'price': 9.99,
                'duration_days': 30,
                'max_patients': 5
            }
        )

        premium_tier, _ = SubscriptionTier.objects.get_or_create(
            name='Premium',
            defaults={
                'description': 'Full access to all features',
                'price': 19.99,
                'duration_days': 30,
                'max_patients': 10
            }
        )

        # Create users with different tiers
        user_tiers = [
            ('free_user@example.com', 'Free User', free_tier),
            ('prime_user@example.com', 'Prime User', prime_tier),
            ('premium_user@example.com', 'Premium User', premium_tier)
        ]

        for email, name, tier in user_tiers:
            user = User.objects.create_user(
                email=email,
                password='testpassword123',
                first_name=name.split()[0],
                last_name=name.split()[1],
                role='PATIENT',
                is_active=True
            )

            patient = Patient.objects.create(
                user=user,
                date_of_birth='1990-01-01',
                gender='M',
                blood_group='O+',
                address=f'{name} Street, City, Country',
                phone_number='+1234567890',
                emergency_contact_name='Emergency Contact',
                emergency_contact_number='+9876543210',
                vitiligo_onset_date='2022-01-01',
                vitiligo_type='Non-segmental',
                affected_body_areas='Hands'
            )

            subscription = Subscription.objects.create(
                user=user,
                tier=tier,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=tier.duration_days),
                is_active=True,
                auto_renew=tier.name != 'Free',
                billing_cycle='monthly',  # Set a default billing cycle for all tiers
                last_billing_date=timezone.now(),
                next_billing_date=timezone.now() + timezone.timedelta(days=30),
                is_trial=False
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created {tier.name} tier user: {email}'))

        self.stdout.write(self.style.SUCCESS('All sample data created successfully!'))