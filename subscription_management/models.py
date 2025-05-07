from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class SubscriptionTier(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    max_patients = models.PositiveIntegerField(help_text="Maximum number of patients allowed for this tier")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SubscriptionFeature(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    tiers = models.ManyToManyField(SubscriptionTier, related_name='features')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)
    billing_cycle = models.CharField(max_length=20, choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly')
    last_billing_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.tier.name}"

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()

    def clean(self):
        if self.is_trial and not self.trial_end_date:
            raise ValidationError("Trial end date is required for trial subscriptions.")

class SubscriptionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_history')
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.tier.name} ({self.start_date.date()} to {self.end_date.date()})"

class FeatureUsage(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='feature_usage')
    feature = models.ForeignKey(SubscriptionFeature, on_delete=models.CASCADE)
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subscription', 'feature')

    def __str__(self):
        return f"{self.subscription.user.email} - {self.feature.name} Usage"

class SubscriptionAddOn(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SubscriptionAddOnPurchase(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='add_on_purchases')
    add_on = models.ForeignKey(SubscriptionAddOn, on_delete=models.PROTECT)
    purchase_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.subscription.user.email} - {self.add_on.name}"

class SubscriptionCommunication(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='communications')
    communication_type = models.CharField(max_length=50, choices=[
        ('welcome', 'Welcome'),
        ('renewal_reminder', 'Renewal Reminder'),
        ('payment_failed', 'Payment Failed'),
        ('cancellation', 'Cancellation'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade')
    ])
    sent_date = models.DateTimeField(auto_now_add=True)
    content = models.TextField()

    def __str__(self):
        return f"{self.subscription.user.email} - {self.get_communication_type_display()}"