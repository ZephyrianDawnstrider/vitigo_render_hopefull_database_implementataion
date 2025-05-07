from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class GSTRate(models.Model):
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.rate}% - {self.description}"

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='invoices',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    invoice_number = models.CharField(max_length=20, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_with_gst = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} for {self.patient.user.get_full_name()}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.ForeignKey(GSTRate, on_delete=models.SET_NULL, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('NEFT', 'NEFT'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('CHEQUE', 'Cheque'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    upi_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Payment of {self.amount} for Invoice {self.invoice.invoice_number}"

class Expense(models.Model):
    EXPENSE_CATEGORY_CHOICES = [
        ('RENT', 'Rent'),
        ('UTILITIES', 'Utilities'),
        ('SALARIES', 'Salaries'),
        ('SUPPLIES', 'Medical Supplies'),
        ('EQUIPMENT', 'Equipment'),
        ('MAINTENANCE', 'Maintenance'),
        ('MARKETING', 'Marketing'),
        ('OTHER', 'Other'),
    ]

    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField()
    vendor = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_expenses')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} Expense: {self.amount} on {self.date}"

class TDSEntry(models.Model):
    TDS_RATE_CHOICES = [
        (0.1, '0.1%'),
        (1, '1%'),
        (2, '2%'),
        (5, '5%'),
        (10, '10%'),
    ]

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='tds_entries')
    tds_rate = models.DecimalField(max_digits=4, decimal_places=2, choices=TDS_RATE_CHOICES)
    tds_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_deducted = models.DateField()

    def __str__(self):
        return f"TDS for {self.expense} at {self.tds_rate}%"

class FinancialYear(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"FY {self.start_date.year}-{self.end_date.year}"

class FinancialReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
        ('CUSTOM', 'Custom'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE, related_name='reports')
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    total_gst_collected = models.DecimalField(max_digits=12, decimal_places=2)
    total_tds_deducted = models.DecimalField(max_digits=12, decimal_places=2)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    report_file = models.FileField(upload_to='financial_reports/', null=True, blank=True)

    def __str__(self):
        return f"{self.report_type} Financial Report: {self.start_date} to {self.end_date}"