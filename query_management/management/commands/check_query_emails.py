# query_management/management/commands/check_query_emails.py

import logging
import email
import imaplib
import json
import re
import string
import random
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from query_management.models import Query, QueryTag
from user_management.models import CustomUser
from access_control.models import Role

logger = logging.getLogger(__name__)
User = get_user_model()

class UserManager:
    @staticmethod
    def generate_random_password(length=12):
        """Generate a secure random password"""
        characters = string.ascii_letters + string.digits + string.punctuation
        while True:
            password = ''.join(random.choice(characters) for i in range(length))
            # Check if password contains at least one of each required type
            if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
                return password

    @staticmethod
    def extract_user_info(email_body):
        """Extract user information from email body"""
        info = {
            'email': None,
            'phone_number': None,
            'first_name': None,
            'last_name': None,
            'country_code': '+91'  # Default country code
        }
        
        try:
            # Extract phone number using regex
            phone_matches = re.findall(r'(?:Contact|Phone|Mobile):\s*([+\d\s-]+)', email_body, re.IGNORECASE)
            if phone_matches:
                phone = re.sub(r'[^\d+]', '', phone_matches[0])
                if phone.startswith('+91'):
                    info['country_code'] = '+91'
                    info['phone_number'] = phone[3:]
                else:
                    info['phone_number'] = phone
            
            # Extract name if provided
            name_matches = re.findall(r'Name:\s*([^\n]+)', email_body, re.IGNORECASE)
            if name_matches:
                full_name = name_matches[0].strip().split(' ', 1)
                info['first_name'] = full_name[0]
                info['last_name'] = full_name[1] if len(full_name) > 1 else ''
                
        except Exception as e:
            logger.error(f"Error extracting user info: {str(e)}")
            
        return info

    @staticmethod
    def get_or_create_user(email, phone_number=None, first_name=None, last_name=None, country_code='+91'):
        """Get existing user or create new one"""
        try:
            # Try to find user by email
            user = User.objects.filter(email=email).first()
            if user:
                logger.info(f"Found existing user with email: {email}")
                return user, False

            # Try to find user by phone number if provided
            if phone_number:
                user = User.objects.filter(phone_number=phone_number).first()
                if user:
                    logger.info(f"Found existing user with phone: {phone_number}")
                    return user, False

            # Get the patient role
            patient_role = Role.objects.get(name='PATIENT')
            
            # Create new user
            with transaction.atomic():
                # Generate a secure random password
                password = UserManager.generate_random_password()
                user = User.objects.create_user(
                    email=email,
                    password=password,  # Use our generated password
                    first_name=first_name or email.split('@')[0],
                    last_name=last_name or '',
                    phone_number=phone_number or '',
                    country_code=country_code,
                    role=patient_role
                )
                logger.info(f"Created new user with email: {email}")
                return user, True

        except Exception as e:
            logger.error(f"Error in get_or_create_user: {str(e)}")
            raise

class EmailQueryHandler:
    def __init__(self):
        self.email_host = 'imap.gmail.com'
        self.email_user = settings.EMAIL_HOST_USER
        self.email_password = settings.EMAIL_HOST_PASSWORD
        self.imap_server = None
        self.log_file = 'email_logs.txt'
        self.user_manager = UserManager()

    def connect(self):
        try:
            logger.info(f"Connecting to {self.email_host}")
            self.imap_server = imaplib.IMAP4_SSL(self.email_host)
            self.imap_server.login(self.email_user, self.email_password)
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            return False

    def disconnect(self):
        if self.imap_server:
            try:
                self.imap_server.logout()
            except Exception as e:
                logger.error(f"Disconnect error: {str(e)}")

    def get_email_body(self, email_message):
        """Extract email body from message"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode()
            return email_message.get_payload(decode=True).decode()
        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")
            return ""

    def log_todays_emails(self):
        """Log all of today's emails to file with error handling"""
        if not self.connect():
            logger.error("Failed to connect to email server")
            return

        try:
            # Clear existing log file
            with open(self.log_file, 'w') as f:
                f.write('')  # Safely clear file
            
            self.imap_server.select('INBOX')
            today = timezone.now().strftime("%d-%b-%Y")
            status, message_numbers = self.imap_server.search(None, f'(SINCE "{today}")')
            
            if status != 'OK':
                logger.error(f"Failed to search emails: {status}")
                return

            if not message_numbers[0]:
                logger.info("No messages found today")
                return

            messages = message_numbers[0].split()
            logger.info(f"Found {len(messages)} messages today")

            for num in messages:
                try:
                    status, msg = self.imap_server.fetch(num, '(RFC822 FLAGS)')
                    if status != 'OK':
                        logger.error(f"Failed to fetch message {num}: {status}")
                        continue

                    email_body = msg[0][1]
                    flags = imaplib.ParseFlags(msg[0][0])
                    email_message = email.message_from_bytes(email_body)

                    # Get email details with error handling
                    try:
                        subject = str(email.header.make_header(
                            email.header.decode_header(email_message['subject'])))
                    except:
                        subject = "No Subject"
                        logger.warning(f"Could not decode subject for message {num}")

                    try:
                        from_address = email.utils.parseaddr(email_message['from'])[1]
                    except:
                        from_address = "unknown@email.com"
                        logger.warning(f"Could not parse from address for message {num}")

                    date = email_message.get('date', timezone.now().strftime("%Y-%m-%d %H:%M:%S"))
                    is_read = '\\Seen' in flags
                    body = self.get_email_body(email_message)

                    # Log to file
                    log_entry = {
                        'message_id': num.decode(),
                        'subject': subject,
                        'from': from_address,
                        'date': date,
                        'is_read': is_read,
                        'body': body
                    }

                    with open(self.log_file, 'a') as f:
                        f.write(json.dumps(log_entry) + '\n')

                except Exception as e:
                    logger.error(f"Error processing message {num}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in log_todays_emails: {str(e)}")
        finally:
            self.disconnect()

    def determine_priority(self, subject, body):
        """Determine query priority based on content"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # High priority keywords
        if any(word in subject_lower or word in body_lower for word in 
               ['urgent', 'emergency', 'immediate', 'critical']):
            return 'A'
        
        # Low priority keywords
        if any(word in subject_lower or word in body_lower for word in 
               ['feedback', 'suggestion', 'general', 'inquiry']):
            return 'C'
        
        # Default to medium priority
        return 'B'

    def determine_query_type(self, subject, body):
        """Determine query type based on content"""
        content = (subject + ' ' + body).lower()
        
        if any(word in content for word in ['appointment', 'schedule', 'booking']):
            return 'APPOINTMENT'
        elif any(word in content for word in ['treatment', 'medicine', 'prescription']):
            return 'TREATMENT'
        elif any(word in content for word in ['bill', 'payment', 'cost', 'price']):
            return 'BILLING'
        elif any(word in content for word in ['complaint', 'issue', 'problem']):
            return 'COMPLAINT'
        elif any(word in content for word in ['feedback', 'suggestion']):
            return 'FEEDBACK'
        
        return 'GENERAL'

    def process_logged_emails(self):
        """Process the logged emails and create queries"""
        try:
            if not self.connect():
                return

            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        email_data = json.loads(line.strip())
                        
                        # Check if it's a query email and not read
                        if '[VITIGO-QUERY]' in email_data['subject'].upper() and not email_data['is_read']:
                            logger.info(f"Processing query email: {email_data['subject']}")

                            # Check if query already exists for this email message
                            message_id = email_data['message_id']
                            message_id_marker = f"\n\nMessage-ID: {message_id}"
                            
                            # Check if any query exists with this message ID in description
                            if Query.objects.filter(
                                description__endswith=message_id_marker,
                                source='EMAIL'
                            ).exists():
                                logger.info(f"Query already exists for message ID {message_id}")
                                continue

                            # Extract user information
                            user_info = UserManager.extract_user_info(email_data['body'])
                            user_info['email'] = email_data['from']

                            # Get or create user
                            user, is_new_user = UserManager.get_or_create_user(**user_info)

                            # Clean subject and determine query details
                            clean_subject = email_data['subject'].split(']', 1)[1].strip()
                            query_type = self.determine_query_type(clean_subject, email_data['body'])
                            priority = self.determine_priority(clean_subject, email_data['body'])

                            # Create description with message ID appended
                            description = email_data['body'] + message_id_marker

                            # Create query with transaction
                            with transaction.atomic():
                                query = Query.objects.create(
                                    user=user,
                                    subject=clean_subject[:255],
                                    description=description,  # Description now includes message ID
                                    source='EMAIL',
                                    contact_email=email_data['from'],
                                    contact_phone=user_info['phone_number'],
                                    status='NEW',
                                    is_anonymous=False,
                                    query_type=query_type,
                                    priority=priority,
                                    is_patient=True
                                )

                                # Add relevant tags
                                if is_new_user:
                                    tag, _ = QueryTag.objects.get_or_create(name='New Patient')
                                    query.tags.add(tag)

                            # Mark email as read in Gmail
                            self.imap_server.select('INBOX')
                            self.imap_server.store(message_id.encode(), '+FLAGS', '\\Seen')
                            
                            logger.info(f"Created query {query.query_id} for user {user.email}")

                    except json.JSONDecodeError:
                        logger.error("Error decoding JSON line")
                    except Exception as e:
                        logger.error(f"Error processing logged email: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Error in process_logged_emails: {str(e)}")
        finally:
            self.disconnect()

class Command(BaseCommand):
    help = 'Process query emails and create Query objects'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write("Starting email processing...")
            handler = EmailQueryHandler()
            
            # Step 1: Log all today's emails
            self.stdout.write("Logging today's emails...")
            handler.log_todays_emails()
            
            # Step 2: Process the logged emails
            self.stdout.write("Processing logged emails...")
            handler.process_logged_emails()
            
            self.stdout.write(self.style.SUCCESS('Successfully processed emails'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))