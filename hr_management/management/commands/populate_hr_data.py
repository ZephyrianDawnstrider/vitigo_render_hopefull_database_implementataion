import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from faker import Faker

from hr_management.models import (
    Department, Position, Employee, Attendance, Leave, PayrollPeriod,
    Payroll, PerformanceReview, Training, TrainingParticipant,
    Document, Grievance, AssetAssignment, EmployeeSkill
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Populate HR management system with sample data'

    def __init__(self):
        super().__init__()
        self.departments = []
        self.positions = []
        self.employees = []
        self.trainings = []

    def clear_existing_data(self):
        """Clear all existing HR data"""
        try:
            logger.info("Clearing existing HR data...")
            # Delete in reverse order of dependencies
            AssetAssignment.objects.all().delete()
            Grievance.objects.all().delete()
            PerformanceReview.objects.all().delete()
            Payroll.objects.all().delete()
            PayrollPeriod.objects.all().delete()
            EmployeeSkill.objects.all().delete()
            Document.objects.all().delete()
            TrainingParticipant.objects.all().delete()
            Training.objects.all().delete()
            Attendance.objects.all().delete()
            Leave.objects.all().delete()
            Employee.objects.all().delete()
            Position.objects.all().delete()
            Department.objects.all().delete()
            logger.info("Successfully cleared existing HR data")
        except Exception as e:
            logger.error(f"Error clearing existing data: {str(e)}")
            raise

    def get_random_non_patient_users(self, count=1):
        """Get random users who are not patients"""
        try:
            users = User.objects.exclude(role__name='Patient').filter(is_active=True)
            return random.sample(list(users), min(count, users.count()))
        except Exception as e:
            logger.error(f"Error getting non-patient users: {str(e)}")
            return []

    @transaction.atomic
    def create_departments(self):
        """Create sample departments"""
        try:
            department_data = [
                {'name': 'Human Resources', 'code': 'HR'},
                {'name': 'Medical Staff', 'code': 'MED'},
                {'name': 'Administration', 'code': 'ADM'},
                {'name': 'Laboratory', 'code': 'LAB'},
                {'name': 'Pharmacy', 'code': 'PHR'},
                {'name': 'Reception', 'code': 'REC'},
            ]

            for data in department_data:
                head = random.choice(self.get_random_non_patient_users())
                dept = Department.objects.create(
                    name=data['name'],
                    code=data['code'],
                    description=fake.text(max_nb_chars=200),
                    head=head
                )
                self.departments.append(dept)
                logger.info(f"Created department: {dept.name}")

        except Exception as e:
            logger.error(f"Error creating departments: {str(e)}")
            raise

    @transaction.atomic
    def create_positions(self):
        """Create sample positions"""
        try:
            for dept in self.departments:
                for _ in range(3):
                    position = Position.objects.create(
                        title=fake.job(),
                        department=dept,
                        description=fake.text(),
                        requirements=fake.text(),
                        responsibilities=fake.text(),
                        min_salary=Decimal(random.randint(30000, 50000)),
                        max_salary=Decimal(random.randint(51000, 100000))
                    )
                    self.positions.append(position)
                    logger.info(f"Created position: {position.title}")

        except Exception as e:
            logger.error(f"Error creating positions: {str(e)}")
            raise

    @transaction.atomic
    def create_employees(self):
        """Create sample employees"""
        try:
            users = self.get_random_non_patient_users(20)
            for user in users:
                position = random.choice(self.positions)
                employee = Employee.objects.create(
                    user=user,
                    employee_id=f"EMP{random.randint(1000, 9999)}",
                    department=position.department,
                    position=position,
                    date_of_birth=fake.date_of_birth(minimum_age=22, maximum_age=65),
                    emergency_contact_name=fake.name(),
                    emergency_contact_number=fake.phone_number(),
                    address=fake.address(),
                    employment_status=random.choice([x[0] for x in Employee.EMPLOYMENT_STATUS]),
                    employment_type=random.choice([x[0] for x in Employee.EMPLOYMENT_TYPE]),
                    join_date=fake.date_between(start_date='-5y', end_date='today'),
                    current_salary=Decimal(random.randint(30000, 100000))
                )
                self.employees.append(employee)
                logger.info(f"Created employee: {employee.employee_id}")

        except Exception as e:
            logger.error(f"Error creating employees: {str(e)}")
            raise

    @transaction.atomic
    def create_attendance_records(self):
        """Create sample attendance records"""
        try:
            for employee in self.employees:
                # Generate a list of unique dates for the last 30 days
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)
                dates = [start_date + timedelta(days=x) for x in range(31)]
                
                for date in dates:
                    # Create timezone-aware base times using timezone.now()
                    base_time = timezone.now()
                    base_check_in = base_time.replace(
                        year=date.year,
                        month=date.month,
                        day=date.day,
                        hour=9,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    base_check_out = base_time.replace(
                        year=date.year,
                        month=date.month,
                        day=date.day,
                        hour=17,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    
                    # Randomize check-in time between 8:45 and 9:15
                    check_in = base_check_in + timedelta(minutes=random.randint(-15, 15))
                    # Randomize check-out time between 16:45 and 17:15
                    check_out = base_check_out + timedelta(minutes=random.randint(-15, 15))
                    
                    # Determine status based on check-in time
                    if check_in > (base_check_in + timedelta(minutes=15)):
                        status = 'LATE'
                    else:
                        status = random.choice(['PRESENT', 'PRESENT', 'PRESENT', 'HALF_DAY'])
                    
                    Attendance.objects.create(
                        employee=employee,
                        date=date,
                        check_in=check_in,
                        check_out=check_out,
                        status=status
                    )
            logger.info("Created attendance records")

        except Exception as e:
            logger.error(f"Error creating attendance records: {str(e)}")
            raise

    @transaction.atomic
    def create_leaves(self):
        """Create sample leave records"""
        try:
            for employee in self.employees:
                for _ in range(random.randint(1, 5)):
                    start_date = fake.date_between(start_date='-60d', end_date='+60d')
                    end_date = start_date + timedelta(days=random.randint(1, 5))
                    Leave.objects.create(
                        employee=employee,
                        leave_type=random.choice([x[0] for x in Leave.LEAVE_TYPE_CHOICES]),
                        start_date=start_date,
                        end_date=end_date,
                        reason=fake.text(max_nb_chars=100),
                        status=random.choice([x[0] for x in Leave.STATUS_CHOICES])
                    )
            logger.info("Created leave records")

        except Exception as e:
            logger.error(f"Error creating leave records: {str(e)}")
            raise

    @transaction.atomic
    def create_trainings(self):
        """Create sample training programs"""
        try:
            for _ in range(5):
                start_date = fake.date_between(start_date='-30d', end_date='+90d')
                training = Training.objects.create(
                    title=fake.catch_phrase(),
                    description=fake.text(),
                    trainer=fake.name(),
                    start_date=start_date,
                    end_date=start_date + timedelta(days=random.randint(1, 5)),
                    location=fake.address(),
                    max_participants=random.randint(5, 20),
                    status=random.choice(['PLANNED', 'IN_PROGRESS', 'COMPLETED'])
                )
                self.trainings.append(training)
                
                # Add random participants
                for employee in random.sample(self.employees, random.randint(3, 10)):
                    TrainingParticipant.objects.create(
                        training=training,
                        employee=employee,
                        status=random.choice(['ENROLLED', 'COMPLETED'])
                    )
            logger.info("Created training programs and participants")

        except Exception as e:
            logger.error(f"Error creating training programs: {str(e)}")
            raise

    @transaction.atomic
    def create_documents(self):
        """Create sample employee documents"""
        try:
            for employee in self.employees:
                for doc_type in ['IDENTIFICATION', 'EDUCATIONAL', 'PROFESSIONAL']:
                    Document.objects.create(
                        employee=employee,
                        document_type=doc_type,
                        title=f"{doc_type.title()} Document",
                        description=fake.text(max_nb_chars=100),
                        expiry_date=fake.date_between(start_date='today', end_date='+5y')
                    )
            logger.info("Created employee documents")

        except Exception as e:
            logger.error(f"Error creating documents: {str(e)}")
            raise

    @transaction.atomic
    def create_skills(self):
        """Create sample employee skills"""
        try:
            skills = ['Communication', 'Leadership', 'Problem Solving', 'Team Management', 
                     'Technical Skills', 'Customer Service', 'Project Management']
            
            for employee in self.employees:
                for skill in random.sample(skills, random.randint(2, 5)):
                    EmployeeSkill.objects.create(
                        employee=employee,
                        skill_name=skill,
                        proficiency_level=random.randint(1, 5),
                        years_of_experience=Decimal(random.randint(1, 10)),
                        is_primary=random.choice([True, False]),
                        certified=random.choice([True, False])
                    )
            logger.info("Created employee skills")

        except Exception as e:
            logger.error(f"Error creating skills: {str(e)}")
            raise

    @transaction.atomic
    def create_payroll_periods(self):
        """Create sample payroll periods"""
        try:
            for month in range(1, 13):
                year = datetime.now().year
                start_date = datetime(year, month, 1).date()
                end_date = (datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)).date() - timedelta(days=1)
                
                PayrollPeriod.objects.create(
                    start_date=start_date,
                    end_date=end_date,
                    is_processed=month < datetime.now().month,
                    processed_at=datetime.now() if month < datetime.now().month else None,
                    processed_by=random.choice(self.get_random_non_patient_users())
                )
            logger.info("Created payroll periods")
        except Exception as e:
            logger.error(f"Error creating payroll periods: {str(e)}")
            raise

    @transaction.atomic
    def create_payrolls(self):
        """Create sample payroll records"""
        try:
            periods = PayrollPeriod.objects.all()
            for employee in self.employees:
                for period in periods:
                    if period.is_processed:
                        allowances = {
                            'transport': random.randint(1000, 3000),
                            'medical': random.randint(2000, 5000),
                            'housing': random.randint(5000, 10000)
                        }
                        deductions = {
                            'tax': random.randint(2000, 5000),
                            'insurance': random.randint(1000, 2000)
                        }
                        basic_salary = float(employee.current_salary) / 12
                        net_salary = (basic_salary + sum(allowances.values()) - sum(deductions.values()))
                        
                        Payroll.objects.create(
                            employee=employee,
                            period=period,
                            basic_salary=basic_salary,
                            allowances=allowances,
                            deductions=deductions,
                            net_salary=net_salary,
                            payment_status='PAID',
                            payment_date=period.end_date
                        )
            logger.info("Created payroll records")
        except Exception as e:
            logger.error(f"Error creating payroll records: {str(e)}")
            raise

    @transaction.atomic
    def create_performance_reviews(self):
        """Create sample performance reviews"""
        try:
            for employee in self.employees:
                review_date = fake.date_between(start_date='-1y', end_date='today')
                PerformanceReview.objects.create(
                    employee=employee,
                    reviewer=random.choice(self.get_random_non_patient_users()),
                    review_date=review_date,
                    review_period_start=review_date - timedelta(days=180),
                    review_period_end=review_date,
                    technical_skills=random.randint(3, 5),
                    communication=random.randint(3, 5),
                    teamwork=random.randint(3, 5),
                    productivity=random.randint(3, 5),
                    reliability=random.randint(3, 5),
                    achievements=fake.text(),
                    areas_for_improvement=fake.text(),
                    goals=fake.text(),
                    overall_comments=fake.text(),
                    status=random.choice(['DRAFT', 'COMPLETED', 'ACKNOWLEDGED'])
                )
            logger.info("Created performance reviews")
        except Exception as e:
            logger.error(f"Error creating performance reviews: {str(e)}")
            raise

    @transaction.atomic
    def create_grievances(self):
        """Create sample grievances"""
        try:
            for employee in random.sample(self.employees, len(self.employees) // 3):
                Grievance.objects.create(
                    employee=employee,
                    subject=fake.sentence(),
                    description=fake.text(),
                    priority=random.choice(['HIGH', 'MEDIUM', 'LOW']),
                    status=random.choice(['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']),
                    assigned_to=random.choice(self.get_random_non_patient_users()),
                    resolution=fake.text() if random.choice([True, False]) else '',
                    is_confidential=random.choice([True, False])
                )
            logger.info("Created grievances")
        except Exception as e:
            logger.error(f"Error creating grievances: {str(e)}")
            raise

    @transaction.atomic
    def create_asset_assignments(self):
        """Create sample asset assignments"""
        try:
            asset_types = ['LAPTOP', 'DESKTOP', 'MOBILE', 'ACCESS_CARD', 'UNIFORM']
            for employee in self.employees:
                for asset_type in random.sample(asset_types, random.randint(1, 3)):
                    assigned_date = fake.date_between(start_date=employee.join_date, end_date='today')
                    AssetAssignment.objects.create(
                        employee=employee,
                        asset_type=asset_type,
                        asset_id=f"{asset_type[:3]}-{random.randint(1000, 9999)}",
                        description=fake.text(),
                        assigned_date=assigned_date,
                        return_due_date=assigned_date + timedelta(days=365),
                        condition_on_assignment='New',
                        assigned_by=random.choice(self.get_random_non_patient_users())
                    )
            logger.info("Created asset assignments")
        except Exception as e:
            logger.error(f"Error creating asset assignments: {str(e)}")
            raise

    def handle(self, *args, **kwargs):
        try:
            logger.info("Starting HR data population...")
            
            # Clear existing data first
            self.clear_existing_data()
            
            # Create new data in order
            self.create_departments()
            self.create_positions()
            self.create_employees()
            self.create_attendance_records()
            self.create_leaves()
            self.create_trainings()
            self.create_documents()
            self.create_skills()
            self.create_payroll_periods()
            self.create_payrolls()
            self.create_performance_reviews()
            self.create_grievances()
            self.create_asset_assignments()
            
            logger.info("Successfully completed HR data population")
            self.stdout.write(self.style.SUCCESS('Successfully populated HR data'))
            
        except Exception as e:
            logger.error(f"Failed to populate HR data: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Failed to populate HR data: {str(e)}'))
