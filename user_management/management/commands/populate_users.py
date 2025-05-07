# user_management/management/commands/populate_users.py
from django.core.management.base import BaseCommand
from user_management.models import CustomUser
from access_control.models import Role
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Populate the database with multiple users with different roles'

    def add_arguments(self, parser):
        parser.add_argument('num_users', type=int, help='The number of users to create')

    def handle(self, *args, **kwargs):
        fake = Faker()
        num_users = kwargs['num_users']
        
        # Get all available roles from the database
        roles = list(Role.objects.all())
        
        if not roles:
            self.stdout.write(self.style.ERROR('No roles found in the database. Please create roles first.'))
            return

        for _ in range(num_users):
            email = fake.email()
            first_name = fake.first_name()
            last_name = fake.last_name()
            password = 'password123'
            role = random.choice(roles)  # Choose a random Role instance

            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role  # Assign the Role instance
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created user {user.email} with role {user.role.name}'))