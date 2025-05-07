# help_support/management/commands/populate_help_support.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from user_management.models import CustomUser
from help_support.models import (
    SupportCategory, SupportTicket, SupportResponse, SupportAttachment, FAQ, KnowledgeBaseArticle, SupportRating
)

class Command(BaseCommand):
    help = 'Generate sample help and support data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample help and support data...')

        # Create sample support categories if they don't exist
        support_categories = [
            {'name': 'Technical Issue', 'description': 'Issues related to technical problems'},
            {'name': 'Billing Inquiry', 'description': 'Questions about billing and payments'},
            {'name': 'General Inquiry', 'description': 'General questions and inquiries'},
        ]
        for sc in support_categories:
            SupportCategory.objects.get_or_create(
                name=sc['name'],
                defaults={'description': sc['description']}
            )

        # Fetch all users and support categories
        users = CustomUser.objects.all()
        support_categories = SupportCategory.objects.all()

        # Create sample support tickets
        for user in users:
            for _ in range(random.randint(1, 5)):  # Generate 1 to 5 tickets per user
                category = random.choice(support_categories)
                ticket = SupportTicket.objects.create(
                    user=user,
                    category=category,
                    subject=f"Sample subject for {category.name}",
                    description='Sample description for support ticket',
                    status=random.choice(['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']),
                    priority=random.choice(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
                )

                # Create sample support responses
                for _ in range(random.randint(1, 3)):  # Generate 1 to 3 responses per ticket
                    response = SupportResponse.objects.create(
                        ticket=ticket,
                        user=random.choice(users) if random.choice([True, False]) else None,
                        message='Sample response message'
                    )

                    # Create sample support attachments
                    for _ in range(random.randint(1, 2)):  # Generate 1 to 2 attachments per response
                        SupportAttachment.objects.create(
                            response=response,
                            file='path/to/sample_file.pdf'
                        )

                # Create sample support rating
                if random.choice([True, False]):
                    SupportRating.objects.create(
                        ticket=ticket,
                        rating=random.randint(1, 5),
                        comments='Sample rating comments'
                    )

        # Create sample FAQs
        for category in support_categories:
            for _ in range(random.randint(1, 5)):  # Generate 1 to 5 FAQs per category
                FAQ.objects.create(
                    question=f"Sample question for {category.name}",
                    answer='Sample answer for FAQ',
                    category=category
                )

        # Create sample knowledge base articles
        for user in users:
            for category in support_categories:
                for _ in range(random.randint(1, 3)):  # Generate 1 to 3 articles per category
                    KnowledgeBaseArticle.objects.create(
                        title=f"Sample article for {category.name}",
                        content='Sample content for knowledge base article',
                        category=category,
                        created_by=user
                    )

        self.stdout.write(self.style.SUCCESS('Successfully generated sample help and support data'))