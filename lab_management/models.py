from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class LabTest(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class LabOrder(models.Model):
    STATUS_CHOICES = [
        ('ORDERED', 'Ordered'),
        ('COLLECTED', 'Sample Collected'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='lab_orders',
        limit_choices_to={'role__name': 'PATIENT'}
    )
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ordered_lab_tests')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ORDERED')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Lab Order for {self.patient.user.get_full_name()} on {self.order_date.date()}"

class LabOrderItem(models.Model):
    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='items')
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.lab_test.name} for {self.lab_order}"

class LabResult(models.Model):
    RESULT_STATUS_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ABNORMAL', 'Abnormal'),
        ('CRITICAL', 'Critical'),
    ]

    lab_order_item = models.OneToOneField(LabOrderItem, on_delete=models.CASCADE, related_name='result')
    value = models.CharField(max_length=255)
    unit = models.CharField(max_length=50)
    reference_range = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=RESULT_STATUS_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='performed_lab_tests')
    performed_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Result for {self.lab_order_item.lab_test.name}"

class LabReport(models.Model):
    UPLOAD_TYPE_CHOICES = [
        ('MANUAL', 'Manual Upload'),
        ('AUTOMATIC', 'Automatic Upload'),
    ]

    lab_order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name='report')
    report_file = models.FileField(upload_to='lab_reports/')
    upload_type = models.CharField(max_length=20, choices=UPLOAD_TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_sent_to_patient = models.BooleanField(default=False)

    def __str__(self):
        return f"Lab Report for {self.lab_order}"

class LabReportComment(models.Model):
    lab_report = models.ForeignKey(LabReport, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.lab_report} by {self.created_by}"