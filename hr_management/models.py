# Standard library imports
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

# Django imports
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Initialize logger
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()

class Department(models.Model):
    """Departments within the clinic"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='headed_departments',
        limit_choices_to={'is_active': True}
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subdepartments'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['code'])]

    def __str__(self):
        return self.name

    def clean(self):
        if self.parent and self.parent == self:
            raise ValidationError("Department cannot be its own parent")

class Position(models.Model):
    """Job positions/titles within the clinic"""
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    min_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    max_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['title', 'department']
        ordering = ['department', 'title']

    def clean(self):
        if self.max_salary < self.min_salary:
            raise ValidationError("Maximum salary cannot be less than minimum salary")

    def __str__(self):
        return f"{self.title} ({self.department.name})"

class Employee(models.Model):
    """Extended employee information beyond User model"""
    EMPLOYMENT_STATUS = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
        ('PROBATION', 'Probation')
    ]

    EMPLOYMENT_TYPE = [
        ('PERMANENT', 'Permanent'),
        ('TEMPORARY', 'Temporary'),
        ('SEASONAL', 'Seasonal')
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    reporting_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    
    # Personal Information
    date_of_birth = models.DateField()
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_number = models.CharField(max_length=20)
    address = models.TextField()
    
    # Employment Information
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE)
    join_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Document Information
    resume = models.FileField(
        upload_to='employee_documents/resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])],
        null=True,
        blank=True
    )
    contract_document = models.FileField(
        upload_to='employee_documents/contracts/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        null=True,
        blank=True
    )

    # Timestamps and metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department', 'position']),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"

    def clean(self):
        if self.end_date and self.end_date < self.join_date:
            raise ValidationError("End date cannot be earlier than join date")
        
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValidationError("Date of birth cannot be in the future")

class Attendance(models.Model):
    """Employee attendance tracking"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PRESENT', 'Present'),
            ('ABSENT', 'Absent'),
            ('HALF_DAY', 'Half Day'),
            ('LATE', 'Late'),
            ('LEAVE', 'Leave')
        ],
        default='PRESENT'
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
        ]

    def clean(self):
        if self.check_out and self.check_out < self.check_in:
            raise ValidationError("Check-out time cannot be earlier than check-in time")

class Leave(models.Model):
    """Employee leave management"""
    LEAVE_TYPE_CHOICES = [
        ('ANNUAL', 'Annual Leave'),
        ('SICK', 'Sick Leave'),
        ('MATERNITY', 'Maternity Leave'),
        ('PATERNITY', 'Paternity Leave'),
        ('UNPAID', 'Unpaid Leave'),
        ('OTHER', 'Other')
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than start date")
        
class LeaveSettings(models.Model):
    """Leave type configuration and policies"""
    leave_type = models.CharField(max_length=20, choices=Leave.LEAVE_TYPE_CHOICES, unique=True)
    annual_allowance = models.PositiveIntegerField(
        help_text="Number of days allowed per year"
    )
    carry_forward_limit = models.PositiveIntegerField(
        default=0,
        help_text="Maximum days that can be carried forward to next year"
    )
    min_service_days = models.PositiveIntegerField(
        default=0,
        help_text="Minimum service days required before leave type becomes available"
    )
    requires_approval = models.BooleanField(default=True)
    requires_documentation = models.BooleanField(default=False)
    documentation_info = models.TextField(
        blank=True,
        help_text="Information about required documentation"
    )
    notice_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Minimum notice period required in days"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Leave Settings"
        ordering = ['leave_type']

    def __str__(self):
        return f"{self.get_leave_type_display()} Settings"

class PayrollPeriod(models.Model):
    """Payroll periods configuration"""
    start_date = models.DateField()
    end_date = models.DateField()
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payrolls'
    )

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_processed']),
        ]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than start date")

class Payroll(models.Model):
    """Employee payroll records"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_records')
    period = models.ForeignKey(PayrollPeriod, on_delete=models.PROTECT, related_name='payrolls')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.JSONField(default=dict)
    deductions = models.JSONField(default=dict)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSED', 'Processed'),
            ('PAID', 'Paid'),
            ('FAILED', 'Failed')
        ],
        default='PENDING'
    )
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'period']
        indexes = [
            models.Index(fields=['employee', 'period']),
            models.Index(fields=['payment_status']),
        ]

class PerformanceReview(models.Model):
    """Employee performance reviews"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews')
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_reviews'
    )
    review_date = models.DateField()
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    
    # Performance metrics (1-5 scale)
    technical_skills = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    teamwork = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    productivity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    reliability = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    achievements = models.TextField()
    areas_for_improvement = models.TextField()
    goals = models.TextField()
    overall_comments = models.TextField()
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', 'Draft'),
            ('COMPLETED', 'Completed'),
            ('ACKNOWLEDGED', 'Acknowledged')
        ],
        default='DRAFT'
    )
    
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'review_date']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        if self.review_period_end < self.review_period_start:
            raise ValidationError("Review period end cannot be earlier than start")

class Training(models.Model):
    """Employee training programs"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    trainer = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=200)
    max_participants = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('PLANNED', 'Planned'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled')
        ],
        default='PLANNED'
    )
    materials = models.FileField(
        upload_to='training_materials/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx'])]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than start date")

class TrainingParticipant(models.Model):
    """Participants in training programs"""
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='participants')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_participations')
    status = models.CharField(
        max_length=20,
        choices=[
            ('ENROLLED', 'Enrolled'),
            ('COMPLETED', 'Completed'),
            ('DROPPED', 'Dropped'),
            ('FAILED', 'Failed')
        ],
        default='ENROLLED'
    )
    enrollment_date = models.DateField(auto_now_add=True)
    completion_date = models.DateField(null=True, blank=True)
    attendance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ['training', 'employee']
        indexes = [
            models.Index(fields=['training', 'status']),
            models.Index(fields=['employee', 'status']),
        ]

    def clean(self):
        if self.completion_date and self.completion_date < self.enrollment_date:
            raise ValidationError("Completion date cannot be earlier than enrollment date")

class Document(models.Model):
    """Employee document management"""
    DOCUMENT_TYPES = [
        ('IDENTIFICATION', 'Identification Documents'),
        ('EDUCATIONAL', 'Educational Certificates'),
        ('PROFESSIONAL', 'Professional Certificates'),
        ('MEDICAL', 'Medical Records'),
        ('CONTRACT', 'Employment Contracts'),
        ('OTHER', 'Other Documents')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to='employee_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    expiry_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        User,  # Add this field
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'document_type']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.title}"

class Grievance(models.Model):
    """Employee grievance tracking"""
    PRIORITY_CHOICES = [
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority')
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='grievances')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    filed_date = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_grievances'
    )
    resolution = models.TextField(blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    is_confidential = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"Grievance by {self.employee.user.get_full_name()} - {self.subject}"

class AssetAssignment(models.Model):
    """Track company assets assigned to employees"""
    ASSET_TYPES = [
        ('LAPTOP', 'Laptop'),
        ('DESKTOP', 'Desktop'),
        ('MOBILE', 'Mobile Device'),
        ('ACCESS_CARD', 'Access Card'),
        ('UNIFORM', 'Uniform'),
        ('OTHER', 'Other Equipment')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_assets')
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    asset_id = models.CharField(max_length=50)
    description = models.TextField()
    assigned_date = models.DateField()
    return_due_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)
    condition_on_assignment = models.TextField()
    condition_on_return = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_assets'
    )

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'asset_type']),
            models.Index(fields=['asset_id']),
        ]

    def clean(self):
        if self.return_due_date and self.return_due_date < self.assigned_date:
            raise ValidationError("Return due date cannot be earlier than assigned date")
        if self.returned_date and self.returned_date < self.assigned_date:
            raise ValidationError("Return date cannot be earlier than assigned date")

class EmployeeSkill(models.Model):
    """Track employee skills and proficiency"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    proficiency_level = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1-5 scale where 5 is expert level"
    )
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0)]
    )
    is_primary = models.BooleanField(default=False)
    certified = models.BooleanField(default=False)
    certification_details = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'skill_name']
        indexes = [
            models.Index(fields=['employee', 'is_primary']),
        ]

    def __str__(self):
        return f"{self.skill_name} - {self.employee.user.get_full_name()}"

class Notice(models.Model):
    """HR notices and announcements"""
    PRIORITY_CHOICES = [
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority')
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_notices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title