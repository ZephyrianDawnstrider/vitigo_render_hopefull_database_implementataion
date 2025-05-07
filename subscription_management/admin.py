from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    SubscriptionTier, SubscriptionFeature, Subscription, SubscriptionHistory,
    FeatureUsage, SubscriptionAddOn, SubscriptionAddOnPurchase, SubscriptionCommunication
)

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'max_patients', 'is_active', 'feature_count')
    list_filter = ('is_active', 'duration_days')
    search_fields = ('name', 'description')
    actions = ['activate_tiers', 'deactivate_tiers']

    def feature_count(self, obj):
        return obj.features.count()
    feature_count.short_description = 'Features'

    def activate_tiers(self, request, queryset):
        queryset.update(is_active=True)
    activate_tiers.short_description = "Activate selected tiers"

    def deactivate_tiers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_tiers.short_description = "Deactivate selected tiers"

@admin.register(SubscriptionFeature)
class SubscriptionFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'tier_count')
    list_filter = ('is_active', 'tiers')
    search_fields = ('name', 'description')
    filter_horizontal = ('tiers',)

    def tier_count(self, obj):
        return obj.tiers.count()
    tier_count.short_description = 'Tiers'

class FeatureUsageInline(admin.TabularInline):
    model = FeatureUsage
    extra = 0
    readonly_fields = ('feature', 'usage_count', 'last_used')

class SubscriptionAddOnPurchaseInline(admin.TabularInline):
    model = SubscriptionAddOnPurchase
    extra = 0
    readonly_fields = ('purchase_date',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'tier', 'start_date', 'end_date', 'is_active', 'is_valid', 'auto_renew')
    list_filter = ('is_active', 'auto_renew', 'tier', 'is_trial')
    search_fields = ('user__email', 'tier__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FeatureUsageInline, SubscriptionAddOnPurchaseInline]
    actions = ['activate_subscriptions', 'deactivate_subscriptions']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'

    def activate_subscriptions(self, request, queryset):
        queryset.update(is_active=True)
    activate_subscriptions.short_description = "Activate selected subscriptions"

    def deactivate_subscriptions(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_subscriptions.short_description = "Deactivate selected subscriptions"

@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'tier', 'start_date', 'end_date', 'amount_paid', 'status', 'transaction_id')
    list_filter = ('status', 'tier', 'start_date')
    search_fields = ('user__email', 'transaction_id')
    readonly_fields = ('created_at',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

@admin.register(SubscriptionAddOn)
class SubscriptionAddOnAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

@admin.register(SubscriptionAddOnPurchase)
class SubscriptionAddOnPurchaseAdmin(admin.ModelAdmin):
    list_display = ('subscription_user', 'add_on', 'purchase_date', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'add_on', 'purchase_date')
    search_fields = ('subscription__user__email', 'add_on__name')

    def subscription_user(self, obj):
        return obj.subscription.user.email
    subscription_user.short_description = 'User'

@admin.register(SubscriptionCommunication)
class SubscriptionCommunicationAdmin(admin.ModelAdmin):
    list_display = ('subscription_user', 'communication_type', 'sent_date')
    list_filter = ('communication_type', 'sent_date')
    search_fields = ('subscription__user__email', 'content')

    def subscription_user(self, obj):
        return obj.subscription.user.email
    subscription_user.short_description = 'User'