from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from faker import Faker
import random
from decimal import Decimal
from django.utils.timezone import make_aware  
from datetime import datetime

from phototherapy_management.models import (
    PhototherapyType, PatientRFIDCard, PhototherapyDevice,
    PhototherapyProtocol, PhototherapyPlan, PhototherapySession,
    HomePhototherapyLog, ProblemReport, PhototherapyPayment,
    PhototherapyReminder, PhototherapyProgress, DeviceMaintenance,
    PhototherapyCenter, PhototherapyPackage
)

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Populate the database with realistic phototherapy data'

    def handle(self, *args, **kwargs):
        # Clear existing data
        self.stdout.write('Clearing existing phototherapy data...')
        try:
            # Delete in proper order to respect foreign key constraints
            PhototherapyReminder.objects.all().delete()
            PhototherapyProgress.objects.all().delete()
            DeviceMaintenance.objects.all().delete()
            ProblemReport.objects.all().delete()
            HomePhototherapyLog.objects.all().delete()
            PhototherapyPayment.objects.all().delete()
            PhototherapySession.objects.all().delete()
            PhototherapyPlan.objects.all().delete()
            PatientRFIDCard.objects.all().delete()
            PhototherapyProtocol.objects.all().delete()
            PhototherapyCenter.objects.all().delete()
            PhototherapyPackage.objects.all().delete()  # Add this line
            PhototherapyDevice.objects.all().delete()
            PhototherapyType.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('Successfully cleared all existing phototherapy data'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing existing data: {str(e)}')
            )
            return

        self.stdout.write('Starting to populate phototherapy data...')
        
        # Get random users
        users = list(User.objects.all())
        if not users:
            self.stdout.write('No users found. Please create users first.')
            return

        # Create all data in sequence
        therapy_types = self._create_therapy_types()
        centers = self._create_centers()
        devices = self._create_devices(therapy_types, centers)
        protocols = self._create_protocols(therapy_types)
        packages = self._create_packages()  # Add this line
        rfid_cards = self._create_rfid_cards(users)
        plans = self._create_treatment_plans(users, protocols, rfid_cards, centers)
        sessions = self._create_sessions(plans, devices)
        
        self._create_payments(plans, users)
        self._create_reminders(plans)
        self._create_progress_records(plans, users)
        self._create_maintenance_records(devices, users)

        self.stdout.write(self.style.SUCCESS('Successfully populated phototherapy data'))

    def _create_therapy_types(self):
        """Create realistic phototherapy types"""
        types_data = [
            {
                'name': 'Narrow Band UVB Full Body Cabinet',
                'therapy_type': 'WB_NB',
                'description': 'Full body phototherapy using narrowband UVB (311-313nm). Most effective for widespread vitiligo and psoriasis treatment. Recommended as first-line therapy for most patients.',
                'priority': 'A',
                'requires_rfid': True
            },
            {
                'name': 'XTRAC Excimer Laser',
                'therapy_type': 'EXCIMER',
                'description': 'Targeted 308nm excimer laser therapy for localized areas. Ideal for resistant patches and areas difficult to treat with other methods. High precision with minimal exposure to surrounding skin.',
                'priority': 'A',
                'requires_rfid': False
            },
            {
                'name': 'Home NB-UVB Unit',
                'therapy_type': 'HOME_NB',
                'description': 'Portable narrowband UVB unit for home use. Suitable for stable patients with good compliance history. Requires thorough training and regular monitoring.',
                'priority': 'B',
                'requires_rfid': False
            },
            {
                'name': 'Targeted UVB Spot Treatment',
                'therapy_type': 'WB_NB',
                'description': 'Focused narrowband UVB treatment for small areas using specialized hand-held devices. Perfect for facial and difficult-to-reach areas.',
                'priority': 'B',
                'requires_rfid': True
            }
        ]

        types = []
        for data in types_data:
            therapy_type = PhototherapyType.objects.create(**data)
            types.append(therapy_type)
            self.stdout.write(f'Created therapy type: {therapy_type.name}')
        return types

    def _create_centers(self):
        """Create realistic phototherapy centers"""
        centers_data = [
            {
                'name': 'VitiGo Main Phototherapy Center',
                'address': '42/1 MG Road, Crystal Plaza, Bangalore - 560001',
                'contact_number': '+91 80 2558 7890',
                'email': 'main.center@vitigo.com',
                'operating_hours': 'Monday to Friday: 8:00 AM - 8:00 PM\nSaturday: 9:00 AM - 6:00 PM\nSunday: Closed',
            },
            {
                'name': 'VitiGo Indiranagar Clinic',
                'address': '#123, 100 Feet Road, Indiranagar, Bangalore - 560038',
                'contact_number': '+91 80 2552 1234',
                'email': 'indiranagar@vitigo.com',
                'operating_hours': 'Monday to Saturday: 9:00 AM - 7:00 PM\nSunday: 10:00 AM - 2:00 PM',
            },
            {
                'name': 'VitiGo Whitefield Center',
                'address': 'Forum Value Mall, Whitefield Main Road, Bangalore - 560066',
                'contact_number': '+91 80 2841 5678',
                'email': 'whitefield@vitigo.com',
                'operating_hours': 'Monday to Sunday: 8:30 AM - 8:30 PM',
            }
        ]

        centers = []
        try:
            for data in centers_data:
                center = PhototherapyCenter.objects.create(**data)
                centers.append(center)
                self.stdout.write(f'Created center: {center.name}')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error creating center: {str(e)}')
            )

        return centers

    def _create_devices(self, therapy_types, centers):
        """Create realistic phototherapy devices"""
        devices_data = [
            {
                'name': 'Waldmann UV 7002',
                'model_number': 'UV7002K',
                'serial_number': 'WM22001',
                'phototherapy_type': therapy_types[0],  # Full body NB-UVB
                'location': 'Treatment Room 1',
                'installation_date': '2023-01-15'
            },
            {
                'name': 'XTRAC Velocity Plus',
                'model_number': 'VEL-2023',
                'serial_number': 'XT45892',
                'phototherapy_type': therapy_types[1],  # Excimer
                'location': 'Laser Suite 1',
                'installation_date': '2023-03-20'
            },
            {
                'name': 'Daavlin 3 Series',
                'model_number': 'DV3-311',
                'serial_number': 'DV789456',
                'phototherapy_type': therapy_types[0],  # Full body NB-UVB
                'location': 'Treatment Room 2',
                'installation_date': '2023-02-01'
            },
            {
                'name': 'Dermalight 500',
                'model_number': 'DL500-23',
                'serial_number': 'DL67890',
                'phototherapy_type': therapy_types[2],  # Home unit
                'location': 'Equipment Storage',
                'installation_date': '2023-04-10'
            }
        ]

        devices = []
        locations = ['Room A', 'Room B', 'Room C', 'Room D']
        try:
            for data in devices_data:
                device = PhototherapyDevice.objects.create(**data)
                # Assign device to random center(s)
                num_centers = random.randint(1, 2)  # Device can be in 1-2 centers
                selected_centers = random.sample(centers, num_centers)
                for center in selected_centers:
                    center.available_devices.add(device)
                
                devices.append(device)
                self.stdout.write(f'Created device: {device.name} in {num_centers} center(s)')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error creating device: {str(e)}')
            )
        
        return devices

    def _create_protocols(self, therapy_types):
        """Create realistic phototherapy protocols"""
        protocols_data = [
            {
                'name': 'Standard NB-UVB Protocol',
                'phototherapy_type': therapy_types[0],
                'description': 'Standard narrowband UVB protocol for vitiligo treatment. Starting with low dose and gradual increment based on skin response.',
                'initial_dose': 200,  # mJ/cm²
                'max_dose': 1000,  # mJ/cm²
                'increment_percentage': 10,
                'frequency_per_week': 3,
                'duration_weeks': 24,
                'safety_guidelines': '1. Always wear protective eyewear\n2. Cover sensitive areas\n3. Report any burning or adverse reactions\n4. Avoid sun exposure on treatment days',
            },
            {
                'name': 'Excimer Laser Protocol',
                'phototherapy_type': therapy_types[1],
                'description': 'Targeted excimer laser protocol for resistant patches. Higher doses possible due to targeted nature.',
                'initial_dose': 150,  # mJ/cm²
                'max_dose': 3000,  # mJ/cm²
                'increment_percentage': 15,
                'frequency_per_week': 2,
                'duration_weeks': 12,
                'safety_guidelines': '1. Protect surrounding skin\n2. Use eye protection\n3. Apply sunscreen post-treatment\n4. Report any blistering',
            },
            # Add more realistic protocols...
        ]

        protocols = []
        for data in protocols_data:
            protocol = PhototherapyProtocol.objects.create(**data)
            protocols.append(protocol)
        return protocols

    def _create_rfid_cards(self, users):
        """Create realistic RFID cards with proper formats"""
        cards_data = [
            {
                'card_number': 'RFID-2023-0001',
                'notes': 'Primary card for full-body treatment',
                'expires_at': timezone.now() + timedelta(days=365)
            },
            {
                'card_number': 'RFID-2023-0002',
                'notes': 'Replacement card - previous card damaged',
                'expires_at': timezone.now() + timedelta(days=180)
            },
            {
                'card_number': 'RFID-2023-0003',
                'notes': 'Temporary card for trial treatment',
                'expires_at': timezone.now() + timedelta(days=30)
            }
        ]
        
        cards = []
        for user in random.sample(users, min(len(users), len(cards_data))):
            data = cards_data.pop()
            card = PatientRFIDCard.objects.create(
                patient=user,
                **data
            )
            cards.append(card)
        return cards

    def _create_packages(self):
        """Create realistic treatment packages"""
        packages_data = [
            {
                'name': 'Standard NB-UVB Package',
                'description': 'Complete 36-session package of Narrowband UVB treatment. Includes initial consultation and progress tracking.',
                'number_of_sessions': 36,
                'total_cost': Decimal('18000.00'),
                'is_featured': True,
                'therapy_type': None  # Will be set to NB-UVB type
            },
            {
                'name': 'Excimer Laser Intensive',
                'description': 'Targeted treatment package with 24 sessions of Excimer laser therapy. Best for resistant patches.',
                'number_of_sessions': 24,
                'total_cost': Decimal('24000.00'),
                'is_featured': True,
                'therapy_type': None  # Will be set to Excimer type
            },
            {
                'name': 'Home Therapy Starter',
                'description': 'Initial 12-session package with home phototherapy unit. Includes device training and monitoring.',
                'number_of_sessions': 12,
                'total_cost': Decimal('12000.00'),
                'is_featured': False,
                'therapy_type': None  # Will be set to Home NB type
            }
        ]

        packages = []
        therapy_types = PhototherapyType.objects.all()
        
        for data in packages_data:
            try:
                # Match package with appropriate therapy type
                if 'NB-UVB' in data['name']:
                    data['therapy_type'] = therapy_types.filter(
                        therapy_type='WB_NB',
                        name__icontains='Full Body'
                    ).first()
                elif 'Excimer' in data['name']:
                    data['therapy_type'] = therapy_types.get(therapy_type='EXCIMER')
                elif 'Home' in data['name']:
                    data['therapy_type'] = therapy_types.get(therapy_type='HOME_NB')
                
                if data['therapy_type']:
                    package = PhototherapyPackage.objects.create(**data)
                    packages.append(package)
                    self.stdout.write(f'Created package: {package.name} for {package.therapy_type.name}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Could not find matching therapy type for package: {data["name"]}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error creating package {data["name"]}: {str(e)}')
                )
                continue
        
        return packages

    def _create_treatment_plans(self, users, protocols, rfid_cards, centers):
        """Create realistic treatment plans"""
        plans_data = [
            {
                'current_dose': 250,  # mJ/cm²
                'total_sessions_planned': 36,
                'total_cost': Decimal('18000.00'),
                'special_instructions': 'Patient has sensitive skin. Start with lower doses and monitor closely.',
                'billing_status': 'PARTIAL',
                'reminder_frequency': 1
            },
            {
                'current_dose': 300,  # mJ/cm²
                'total_sessions_planned': 24,
                'total_cost': Decimal('24000.00'),
                'special_instructions': 'Previous good response to NB-UVB. Continue with standard protocol.',
                'billing_status': 'PAID',
                'reminder_frequency': 2
            }
        ]

        plans = []
        for user in random.sample(users, len(users)//3):
            plan_data = random.choice(plans_data)
            plan = PhototherapyPlan.objects.create(
                patient=user,
                protocol=random.choice(protocols),
                rfid_card=random.choice(rfid_cards) if rfid_cards else None,
                start_date=fake.date_between(start_date='-6m'),
                current_dose=plan_data['current_dose'],
                total_sessions_planned=plan_data['total_sessions_planned'],
                total_cost=plan_data['total_cost'],
                billing_status=plan_data['billing_status'],
                special_instructions=plan_data['special_instructions'],
                center=random.choice(centers)  # Assign a random center
            )
            plans.append(plan)
        return plans

    def _create_sessions(self, plans, devices):
        """Create realistic phototherapy sessions"""
        session_remarks = [
            "Patient tolerating treatment well. No adverse effects reported.",
            "Slight erythema noted post-treatment, within expected range.",
            "Patient reported mild itching - monitored for 15 minutes post-treatment.",
            "Reduced dose by 10% due to mild sensitivity from previous session.",
            "Treatment areas showing initial signs of repigmentation.",
            "Patient missed last session due to fever - resumed at previous dose.",
            "Increased exposure time by 10% as per protocol guidelines.",
            "New patch noted on right arm - documented in progress photos.",
            "Patient requested morning sessions for future appointments.",
            "Treatment interrupted due to temporary device error - completed after reset."
        ]

        problem_severities = {
            'NONE': 0.7,    # 70% chance of no problems
            'MILD': 0.2,    # 20% chance of mild problems
            'MODERATE': 0.08, # 8% chance of moderate problems
            'SEVERE': 0.02   # 2% chance of severe problems
        }

        sessions = []
        try:
            # Get eligible staff members first
            excluded_roles = [
                'PATIENT', 'HR_STAFF', 'INVENTORY_MANAGER', 'BILLING_STAFF',
                'LAB_TECHNICIAN', 'PHARMACIST', 'RECEPTIONIST', 'MANAGER'
            ]
            eligible_staff = User.objects.filter(
                is_active=True
            ).exclude(
                role__name__in=excluded_roles
            ).select_related('role')

            if not eligible_staff.exists():
                self.stdout.write(self.style.WARNING('No eligible staff found to administer sessions'))
                return []

            for plan in plans:
                for i in range(random.randint(5, 15)):
                    session_date = fake.date_between(start_date='-3m')
                    # Generate some sample remarks
                    remarks = random.choice(session_remarks)
                    
                    session = PhototherapySession.objects.create(
                        plan=plan,
                        session_number=i+1,
                        scheduled_date=session_date,
                        scheduled_time=fake.time(),
                        device=random.choice(devices),
                        planned_dose=random.uniform(100, 500),
                        actual_dose=random.uniform(100, 500),
                        duration_seconds=random.randint(60, 300),
                        status=random.choice(['COMPLETED', 'MISSED', 'SCHEDULED']),
                        problem_severity=random.choices(list(problem_severities.keys()), list(problem_severities.values()))[0],
                        administered_by=random.choice(eligible_staff),
                        actual_date=session_date,
                        remarks=remarks  # Add remarks here
                    )
                    sessions.append(session)
                    self.stdout.write(f'Created session {session.session_number} for plan {plan.id} with administrator {session.administered_by.get_full_name()}')

            return sessions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating sessions: {str(e)}')
            )
            return []

    def _create_home_logs(self, plans):
        """Create realistic home phototherapy logs"""
        body_areas = [
            "Face and neck",
            "Arms (bilateral)",
            "Legs (bilateral)",
            "Trunk - anterior",
            "Trunk - posterior",
            "Hands and fingers",
            "Feet and toes"
        ]
        
        notes_templates = [
            "Followed recommended exposure time. No issues noted.",
            "Slight tingling sensation during treatment, subsided after 30 minutes.",
            "Skipped exposed areas as instructed. Using sunscreen post-treatment.",
            "Reduced exposure time due to mild sensitivity from previous session.",
            "Treatment areas showing good response. Continuing as prescribed."
        ]
        
        side_effects_templates = [
            "None observed",
            "Mild erythema - resolved within 2 hours",
            "Slight itching post-treatment",
            "Temporary skin dryness",
            "Minor warmth sensation during treatment"
        ]

        for plan in plans:
            # Only create home logs for HOME_NB type treatments
            if plan.protocol.phototherapy_type.therapy_type != 'HOME_NB':
                continue
                
            for _ in range(random.randint(12, 20)):  # More realistic number of sessions
                HomePhototherapyLog.objects.create(
                    plan=plan,
                    date=fake.date_between(start_date='-3m'),
                    time=fake.time_object(end_datetime=None),  # More realistic times
                    duration_minutes=random.choice([10, 15, 20, 25, 30]),  # Standard durations
                    exposure_type='UVB_DEVICE',  # Most home treatments use devices
                    body_areas_treated=", ".join(random.sample(body_areas, random.randint(1, 3))),
                    notes=random.choice(notes_templates),
                    side_effects=random.choice(side_effects_templates)
                )

    def _create_problem_reports(self, sessions, users):
        """Create realistic problem reports"""
        problem_templates = {
            'MILD': [
                {
                    'description': 'Patient reported mild skin redness post-treatment',
                    'action': 'Monitored for 30 minutes, redness subsided. No intervention needed.'
                },
                {
                    'description': 'Slight itching sensation during treatment',
                    'action': 'Completed session with normal parameters. Advised to moisturize.'
                }
            ],
            'MODERATE': [
                {
                    'description': 'Persistent erythema lasting more than expected',
                    'action': 'Reduced next session dose by 20%. Scheduled follow-up.'
                },
                {
                    'description': 'Patient experienced burning sensation mid-treatment',
                    'action': 'Session terminated early. Documented affected areas. Modified protocol.'
                }
            ],
            'SEVERE': [
                {
                    'description': 'Blistering observed in treated area',
                    'action': 'Treatment suspended. Immediate medical evaluation completed. Started topical treatment.'
                },
                {
                    'description': 'Severe photosensitivity reaction',
                    'action': 'Emergency protocol initiated. Treatment paused pending dermatologist review.'
                }
            ]
        }

        for session in random.sample(sessions, len(sessions)//4):
            severity = random.choices(
                ['MILD', 'MODERATE', 'SEVERE'], 
                weights=[0.7, 0.25, 0.05]
            )[0]
            
            problem = random.choice(problem_templates[severity])
            
            ProblemReport.objects.create(
                session=session,
                reported_by=random.choice(users),
                problem_description=problem['description'],
                severity=severity,
                action_taken=problem['action'],
                resolved=severity != 'SEVERE',  # Severe cases often pending
                resolution_notes=f"Follow-up completed on {fake.date()}" if severity != 'SEVERE' else None
            )

    def _create_payments(self, plans, users):
        """Create payments with unique receipt numbers"""
        for plan in plans:
            try:
                total_amount = float(plan.total_cost)
                payment_type = random.choice(['FULL', 'PER_SESSION', 'PARTIAL'])
                
                if payment_type == 'FULL':
                    receipt_number = f"RCP-{plan.id}-{int(timezone.now().timestamp())}"
                    # Create timezone-aware datetime
                    payment_date = timezone.now() - timedelta(days=random.randint(1, 90))
                    
                    PhototherapyPayment.objects.create(
                        plan=plan,
                        payment_type='FULL',
                        amount=plan.total_cost,
                        payment_date=payment_date,
                        payment_method=random.choice(['CASH', 'CARD', 'UPI']),
                        transaction_id=f'TXN-{plan.id}-{random.randint(1000, 9999)}',
                        status='COMPLETED',
                        receipt_number=receipt_number,
                        recorded_by=random.choice(users)
                    )
                
                elif payment_type == 'PER_SESSION':
                    completed_sessions = plan.sessions.filter(status='COMPLETED')
                    per_session_amount = total_amount / plan.total_sessions_planned
                    
                    for session in completed_sessions:
                        receipt_number = f"RCP-{plan.id}-{session.id}-{int(timezone.now().timestamp())}"
                        # Convert date to datetime and make timezone-aware
                        if session.actual_date:
                            payment_date = timezone.make_aware(datetime.combine(session.actual_date, datetime.min.time()))
                        else:
                            payment_date = timezone.make_aware(datetime.combine(session.scheduled_date, datetime.min.time()))
                        
                        PhototherapyPayment.objects.create(
                            plan=plan,
                            payment_type='PER_SESSION',
                            session=session,
                            amount=per_session_amount,
                            payment_date=payment_date,
                            payment_method=random.choice(['CASH', 'CARD', 'UPI']),
                            transaction_id=f'TXN-{plan.id}-{session.id}-{random.randint(1000, 9999)}',
                            status='COMPLETED',
                            receipt_number=receipt_number,
                            recorded_by=random.choice(users)
                        )
                
                else:  # PARTIAL payments
                    num_installments = random.randint(3, 4)
                    amount_per_installment = total_amount / num_installments
                    
                    for i in range(num_installments):
                        receipt_number = f"RCP-{plan.id}-INST{i+1}-{int(timezone.now().timestamp())}"
                        payment_date = timezone.now() - timedelta(days=90-i*30)
                        
                        PhototherapyPayment.objects.create(
                            plan=plan,
                            payment_type='PARTIAL',
                            amount=amount_per_installment,
                            payment_date=payment_date,
                            payment_method=random.choice(['CASH', 'CARD', 'UPI']),
                            transaction_id=f'TXN-{plan.id}-INST{i+1}-{random.randint(1000, 9999)}',
                            status='COMPLETED',
                            receipt_number=receipt_number,
                            recorded_by=random.choice(users),
                            is_installment=True,
                            installment_number=i+1,
                            total_installments=num_installments
                        )

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating payment for plan {plan.id}: {str(e)}'))
                continue

    def _create_reminders(self, plans):
        """Create realistic reminders with proper date formatting"""
        reminder_templates = {
            'SESSION': [
                "Dear {patient_name}, your phototherapy session is scheduled for {appointment_time}. Please arrive 10 minutes early.",
                "Reminder: Your vitiligo treatment session is tomorrow at {appointment_time}. Don't forget your protective eyewear.",
            ],
            'PAYMENT': [
                "Dear {patient_name}, your treatment payment of ₹{amount} is due on {payment_date}. Please clear the pending amount.",
                "Payment reminder: Installment #{installment_number} of ₹{amount} is due on {payment_date}.",
            ],
            'FOLLOWUP': [
                "Dear {patient_name}, you have a follow-up assessment scheduled with Dr. {doctor_name} on {appointment_date}.",
                "Progress evaluation reminder: Please visit the clinic on {appointment_date} for your monthly assessment.",
            ]
        }

        for plan in plans:
            for reminder_type in reminder_templates.keys():
                message = random.choice(reminder_templates[reminder_type])
                scheduled_date = timezone.now() + timedelta(days=random.randint(1, 14))
                
                # Format message with proper date handling
                message_data = {
                    'patient_name': plan.patient.get_full_name(),
                    'appointment_time': scheduled_date.strftime("%I:%M %p"),
                    'appointment_date': scheduled_date.strftime("%d-%b-%Y"),
                    'payment_date': scheduled_date.strftime("%d-%b-%Y"),  # Changed from due_date
                    'amount': f"{round(float(plan.total_cost)/4, 2):,.2f}",
                    'installment_number': random.randint(1, 4),
                    'doctor_name': "Dr. Sharma"
                }
                
                try:
                    formatted_message = message.format(**message_data)
                    
                    PhototherapyReminder.objects.create(
                        plan=plan,
                        reminder_type=reminder_type,
                        scheduled_datetime=scheduled_date,
                        message=formatted_message,
                        status=random.choice(['PENDING', 'SENT', 'SENT', 'SENT'])
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error creating reminder for plan {plan.id}: {str(e)}')
                    )
                    continue

    def _create_progress_records(self, plans, users):
        """Create realistic progress tracking records"""
        progress_templates = {
            'EXCELLENT': {
                'range': (75, 100),
                'notes': [
                    "Significant repigmentation observed in all treated areas. Patient very satisfied.",
                    "Excellent response to treatment. Follicular repigmentation spreading well."
                ]
            },
            'GOOD': {
                'range': (50, 74),
                'notes': [
                    "Steady improvement continues. Good repigmentation in most treated areas.",
                    "Positive response to treatment. Some areas showing complete repigmentation."
                ]
            },
            'MODERATE': {
                'range': (25, 49),
                'notes': [
                    "Gradual improvement noted. Some areas responding better than others.",
                    "Moderate progress observed. Adjusted protocol to target resistant patches."
                ]
            },
            'POOR': {
                'range': (1, 24),
                'notes': [
                    "Limited response to treatment. Consider protocol modification.",
                    "Minimal improvement observed. Scheduled for protocol review."
                ]
            }
        }

        side_effects = [
            "No significant side effects reported",
            "Mild erythema post-treatment - resolves within hours",
            "Occasional itching in treated areas",
            "Temporary skin dryness - advised to increase moisturizer use",
            "Slight hyperpigmentation at treatment borders"
        ]

        # Get only doctors with valid roles
        doctors = [
            u for u in users 
            if hasattr(u, 'role') and 
            u.role is not None and 
            hasattr(u.role, 'name') and 
            u.role.name == 'DOCTOR'
        ]
        
        if not doctors:
            self.stdout.write(self.style.WARNING('No doctors found for progress assessment. Using random users instead.'))
            doctors = users  # Fallback to all users if no doctors found

        for plan in plans:
            # Create multiple progress records over time
            for i in range(3):  # Quarterly assessments
                response_level = random.choices(
                    list(progress_templates.keys()),
                    weights=[0.2, 0.4, 0.3, 0.1]
                )[0]
                
                template = progress_templates[response_level]
                improvement = random.uniform(template['range'][0], template['range'][1])
                
                PhototherapyProgress.objects.create(
                    plan=plan,
                    assessment_date=fake.date_between(
                        start_date='-3m',
                        end_date='today'
                    ),
                    response_level=response_level,
                    improvement_percentage=improvement,
                    notes=random.choice(template['notes']),
                    side_effects_noted=random.choice(side_effects),
                    next_assessment_date=fake.date_between(
                        start_date='+1w',
                        end_date='+4w'
                    ),
                    assessed_by=random.choice(doctors)
                )

    def _create_maintenance_records(self, devices, users):
        """Create realistic maintenance records"""
        maintenance_data = [
            {
                'maintenance_type': 'CALIBRATION',
                'description': ('Annual calibration performed. Tested UV output across all ranges. '
                              'Verified timer accuracy. Updated control software to latest version. '
                              'All parameters within acceptable ranges.'),
                'cost': Decimal('12000.00'),
                'parts_replaced': 'UV sensors replaced\nTimer module firmware updated\nControl panel tested',
            },
            {
                'maintenance_type': 'ROUTINE',
                'description': ('Quarterly maintenance check completed. Cleaned all UV bulbs and reflectors. '
                              'Replaced air filters. Tested all safety interlocks. '
                              'Checked and adjusted door seals.'),
                'cost': Decimal('5000.00'),
                'parts_replaced': 'Air filters\nDoor seals',
            },
            {
                'maintenance_type': 'REPAIR',
                'description': ('Emergency repair - UVB bulb replacement. Replaced failed UV tube. '
                              'Tested adjacent tubes for signs of wear. Calibrated new tube output. '
                              'Verified all safety systems.'),
                'cost': Decimal('8000.00'),
                'parts_replaced': 'UVB tube #4\nTube holder\nPower connector',
            }
        ]

        for device in devices:
            data = random.choice(maintenance_data)
            next_date = timezone.now().date() + timedelta(days=90)  # Next maintenance in 90 days
            
            DeviceMaintenance.objects.create(
                device=device,
                maintenance_type=data['maintenance_type'],
                maintenance_date=timezone.now().date() - timedelta(days=random.randint(1, 30)),
                performed_by="Dr. Raj Kumar" if data['maintenance_type'] == 'CALIBRATION' else "Mr. Suresh Technical",
                description=data['description'],
                cost=data['cost'],
                next_maintenance_due=next_date,
                parts_replaced=data['parts_replaced'],
                created_by=random.choice(users)
            )
