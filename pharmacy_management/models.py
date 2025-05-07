# Python standard library imports
from decimal import Decimal

# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

# Get user model
User = get_user_model()

class Medication(models.Model):
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    dosage_form = models.CharField(max_length=100)  
    strength = models.CharField(max_length=50)  
    manufacturer = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    requires_prescription = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.strength} {self.dosage_form}"

    class Meta:
        ordering = ['name']  # Add this inner class to set default ordering

class MedicationStock(models.Model):
    medication = models.OneToOneField(Medication, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    last_restocked = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.medication.name} - Qty: {self.quantity}"

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    expected_delivery_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name} - {self.order_date.date()}"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    def __str__(self):
        return f"{self.medication.name} - Qty: {self.quantity}"

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPE_CHOICES = [
        ('ADD', 'Stock Addition'),
        ('REMOVE', 'Stock Removal'),
        ('CORRECTION', 'Stock Correction'),
    ]

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='stock_adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Use positive number for additions, negative for removals")
    reason = models.TextField()
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    adjusted_at = models.DateTimeField(auto_now_add=True)
    reference_number = models.CharField(max_length=50, blank=True, help_text="External reference number if any")
    
    def save(self, *args, **kwargs):
        # Update the medication stock
        stock = self.medication.stock
        if self.adjustment_type in ['ADD', 'CORRECTION']:
            stock.quantity += self.quantity
        else:
            stock.quantity -= self.quantity
        stock.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.medication.name} ({self.quantity})"

