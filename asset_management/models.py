# Standard library imports
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta

# Django imports
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Initialize logger
logger = logging.getLogger(__name__)

class AssetCategory(models.Model):
    """Categories for different types of assets"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Annual depreciation rate in percentage"
    )
    expected_lifetime_years = models.PositiveIntegerField(
        default=5,
        help_text="Expected useful life of assets in this category"
    )
    maintenance_frequency_days = models.PositiveIntegerField(
        default=365,
        help_text="Recommended days between maintenance checks"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asset Category"
        verbose_name_plural = "Asset Categories"
        ordering = ['name']
        indexes = [models.Index(fields=['code'])]

    def __str__(self):
        return f"{self.name} ({self.code})"

class Asset(models.Model):
    """Core asset information"""
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('UNDER_MAINTENANCE', 'Under Maintenance'),
        ('DAMAGED', 'Damaged'),
        ('RETIRED', 'Retired'),
        ('DISPOSED', 'Disposed')
    ]

    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
        ('DAMAGED', 'Damaged')
    ]

    # Basic Information
    name = models.CharField(max_length=200)
    asset_id = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name='assets'
    )
    description = models.TextField()
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100)
    
    # Purchase Information
    purchase_date = models.DateField()
    purchase_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    warranty_expiry = models.DateField(null=True, blank=True)
    vendor = models.CharField(max_length=100)
    vendor_contact = models.CharField(max_length=200, blank=True)
    
    # Status and Condition
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='AVAILABLE'
    )
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='EXCELLENT'
    )
    location = models.CharField(max_length=100)
    
    # Technical Details
    specifications = models.JSONField(
        default=dict,
        help_text="Technical specifications as JSON"
    )
    power_rating = models.CharField(max_length=50, blank=True)
    dimensions = models.CharField(max_length=50, blank=True)
    weight = models.CharField(max_length=50, blank=True)
    
    # Documentation
    user_manual = models.FileField(
        upload_to='asset_documents/manuals/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    certificate = models.FileField(
        upload_to='asset_documents/certificates/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['asset_id']),
            models.Index(fields=['status']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.asset_id} - {self.name}"

    def clean(self):
        try:
            if self.warranty_expiry and self.warranty_expiry < self.purchase_date:
                raise ValidationError("Warranty expiry cannot be earlier than purchase date")
        except Exception as e:
            logger.error(f"Asset validation error: {str(e)}")
            raise

class MaintenanceSchedule(models.Model):
    """Scheduled maintenance for assets"""
    PRIORITY_CHOICES = [
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority')
    ]

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue')
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules'
    )
    maintenance_type = models.CharField(max_length=100)
    description = models.TextField()
    scheduled_date = models.DateField()
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )
    estimated_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )
    cost_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )
    vendor = models.CharField(max_length=100, blank=True)
    completion_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['asset', 'scheduled_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Maintenance for {self.asset.name} on {self.scheduled_date}"

class AssetDepreciation(models.Model):
    """Track asset depreciation over time"""
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='depreciation_records'
    )
    date = models.DateField()
    current_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    depreciation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    fiscal_year = models.CharField(max_length=10)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['asset', 'fiscal_year']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"Depreciation for {self.asset.name} - {self.fiscal_year}"

class AssetAudit(models.Model):
    """Track physical audits of assets"""
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='audits'
    )
    audit_date = models.DateField()
    location_verified = models.BooleanField(default=False)
    condition_verified = models.BooleanField(default=False)
    discrepancies = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLANNED'
    )
    conducted_by = models.CharField(max_length=100)
    verified_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    photos = models.JSONField(
        default=list,
        help_text="List of photo URLs or references"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-audit_date']
        indexes = [
            models.Index(fields=['asset', 'audit_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Audit for {self.asset.name} on {self.audit_date}"

class InsurancePolicy(models.Model):
    """Insurance information for valuable assets"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('RENEWED', 'Renewed')
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='insurance_policies'
    )
    policy_number = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=100)
    coverage_type = models.CharField(max_length=100)
    coverage_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    premium_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    deductible = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    documents = models.JSONField(
        default=list,
        help_text="List of insurance document references"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Insurance Policy"
        verbose_name_plural = "Insurance Policies"
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['policy_number']),
            models.Index(fields=['asset', 'status']),
        ]

    def __str__(self):
        return f"Insurance for {self.asset.name} - {self.policy_number}"

    def clean(self):
        try:
            if self.end_date <= self.start_date:
                raise ValidationError("End date must be after start date")
        except Exception as e:
            logger.error(f"Insurance policy validation error: {str(e)}")
            raise