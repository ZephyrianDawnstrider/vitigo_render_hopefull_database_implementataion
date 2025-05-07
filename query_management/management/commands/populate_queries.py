import random
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth import get_user_model
from django.utils import timezone
from query_management.models import Query, QueryTag, QueryUpdate
from access_control.models import Role
from itertools import cycle

class Command(BaseCommand):
    help = 'Clear existing queries and populate the Query model with new sample data'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('num_queries', type=int, help='Number of queries to create')
        parser.add_argument('--email', type=str, help='Email of specific user to create queries for (optional)', required=False)
        parser.add_argument(
            '--preserve',
            action='store_true',
            help='Preserve existing queries instead of deleting them'
        )

    def get_users_by_role(self):
        User = get_user_model()
        patient_users = User.objects.filter(role__name='PATIENT', is_active=True)
        staff_users = User.objects.filter(role__name__in=['ADMIN', 'DOCTOR', 'NURSE', 'STAFF'], is_active=True)
        return patient_users, staff_users

    def generate_date_range(self, num_queries):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)  # Last 3 months
        dates = []
        for i in range(num_queries):
            days = (end_date - start_date).days
            random_days = random.randint(0, days)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            date = start_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
            dates.append(date)
        return sorted(dates)  # Sort dates chronologically

    def handle(self, *args, **kwargs):
        num_queries = kwargs['num_queries']
        preserve_existing = kwargs.get('preserve', False)

        if not preserve_existing:
            # Clear existing data
            self.stdout.write(self.style.WARNING('Clearing existing queries...'))
            deleted_counts = {
                'queries': Query.objects.count(),
                'updates': QueryUpdate.objects.count(),
                'tags': QueryTag.objects.count()
            }
            
            QueryUpdate.objects.all().delete()
            Query.objects.all().delete()
            QueryTag.objects.all().delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleared {deleted_counts["queries"]} queries, '
                    f'{deleted_counts["updates"]} updates, and '
                    f'{deleted_counts["tags"]} tags'
                )
            )

        patient_users, staff_users = self.get_users_by_role()

        if not staff_users.exists():
            self.stdout.write(self.style.ERROR('No staff users found. Please create staff users first.'))
            return
        if not patient_users.exists():
            self.stdout.write(self.style.ERROR('No patient users found. Please create patient users first.'))
            return

        # Create cyclers for each choice type to ensure even distribution
        priorities = cycle([p[0] for p in Query.PRIORITY_CHOICES])
        sources = cycle([s[0] for s in Query.SOURCE_CHOICES])
        statuses = cycle([s[0] for s in Query.STATUS_CHOICES])
        query_types = cycle([t[0] for t in Query.QUERY_TYPE_CHOICES])

        # Sample data
        subjects = {
            'GENERAL': ['General information request', 'Service inquiry', 'Policy question'],
            'APPOINTMENT': ['New appointment request', 'Reschedule appointment', 'Cancel appointment'],
            'TREATMENT': ['Treatment plan inquiry', 'Medicine consultation', 'Side effects query'],
            'BILLING': ['Invoice clarification', 'Payment issue', 'Insurance coverage'],
            'COMPLAINT': ['Service complaint', 'Staff feedback', 'Facility issue'],
            'FEEDBACK': ['Service feedback', 'Staff appreciation', 'Suggestion'],
            'OTHER': ['Documentation request', 'External referral', 'Miscellaneous']
        }

        # Create sample tags
        tags = []
        for tag_name in ['Urgent', 'Follow-up', 'Billing', 'Treatment', 'Administrative', 'Technical']:
            tag, _ = QueryTag.objects.get_or_create(name=tag_name)
            tags.append(tag)

        # Generate chronological dates
        dates = self.generate_date_range(num_queries)
        
        queries_created = 0
        errors = 0

        for i, created_at in enumerate(dates):
            try:
                # Determine if this query is from a patient or other user
                is_patient_query = random.choice([True, False])
                user = random.choice(patient_users if is_patient_query else staff_users)
                assigned_to = random.choice(staff_users)

                # Get next values from cyclers
                priority = next(priorities)
                source = next(sources)
                status = next(statuses)
                query_type = next(query_types)

                # Select appropriate subject based on query type
                subject = random.choice(subjects[query_type])
                description = f"Detailed description for {subject} submitted via {source}."

                # Create query
                query = Query.objects.create(
                    user=user,
                    assigned_to=assigned_to,
                    subject=subject,
                    description=description,
                    source=source,
                    priority=priority,
                    status=status,
                    query_type=query_type,
                    created_at=created_at,
                    is_anonymous=random.choice([True, False]),
                    contact_email=f"sample{i}@example.com" if random.choice([True, False]) else None,
                    contact_phone=f"+1234567890{i}" if random.choice([True, False]) else None,
                    is_patient=is_patient_query,
                    conversion_status=random.choice([True, False]),
                    satisfaction_rating=random.choice([None, 1, 2, 3, 4, 5]),
                    expected_response_date=created_at + timedelta(days=random.randint(1, 5))
                )

                # Add random tags (1-3 tags per query)
                for tag in random.sample(tags, random.randint(1, 3)):
                    query.tags.add(tag)

                # Add updates based on status
                if status in ['IN_PROGRESS', 'WAITING', 'RESOLVED', 'CLOSED']:
                    num_updates = random.randint(1, 3)
                    for j in range(num_updates):
                        update_time = created_at + timedelta(hours=random.randint(1, 24))
                        QueryUpdate.objects.create(
                            query=query,
                            user=random.choice(staff_users),
                            content=f"Update {j+1}: Processing query {query.query_id}",
                            created_at=update_time
                        )

                # Handle resolved/closed queries
                if status in ['RESOLVED', 'CLOSED']:
                    query.resolved_at = created_at + timedelta(days=random.randint(1, 3))
                    query.resolution_summary = f"Query has been {status.lower()} successfully."
                    query.response_time = query.resolved_at - created_at
                    query.save()

                queries_created += 1
                if queries_created % 10 == 0:
                    self.stdout.write(self.style.SUCCESS(f'Created {queries_created} queries...'))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'Error creating query: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {queries_created} queries with {errors} errors'
        ))