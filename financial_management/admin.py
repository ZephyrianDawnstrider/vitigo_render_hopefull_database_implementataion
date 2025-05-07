from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    GSTRate, Invoice, InvoiceItem, Payment, Expense, TDSEntry,
    FinancialYear, FinancialReport
)

@admin.register(GSTRate)
class GSTRateAdmin(admin.ModelAdmin):
    list_display = ('rate', 'description')
    search_fields = ('description',)

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient_link', 'invoice_date', 'due_date', 'status', 'total_with_gst')
    list_filter = ('status', 'invoice_date', 'due_date')
    search_fields = ('invoice_number', 'patient__user__first_name', 'patient__user__last_name')
    inlines = [InvoiceItemInline, PaymentInline]
    readonly_fields = ('created_at', 'updated_at', 'created_by')

    fieldsets = (
        (None, {
            'fields': ('patient', 'invoice_number', 'invoice_date', 'due_date', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_gst_amount', 'total_with_gst')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms_and_conditions', 'created_by', 'created_at', 'updated_at')
        }),
    )

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice_link', 'amount', 'payment_date', 'payment_method', 'transaction_id', 'received_by')
    list_filter = ('payment_date', 'payment_method')
    search_fields = ('invoice__invoice_number', 'transaction_id', 'cheque_number', 'upi_id')

    def invoice_link(self, obj):
        url = reverse("admin:financial_management_invoice_change", args=[obj.invoice.id])
        return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
    invoice_link.short_description = 'Invoice'

class TDSEntryInline(admin.TabularInline):
    model = TDSEntry
    extra = 1

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'gst_amount', 'total_amount', 'date', 'vendor', 'approved_by')
    list_filter = ('category', 'date', 'payment_method')
    search_fields = ('description', 'vendor', 'invoice_number')
    inlines = [TDSEntryInline]
    readonly_fields = ('created_at', 'created_by')

    fieldsets = (
        (None, {
            'fields': ('category', 'amount', 'gst_amount', 'total_amount', 'date', 'description', 'vendor')
        }),
        ('Payment Details', {
            'fields': ('invoice_number', 'payment_method', 'receipt')
        }),
        ('Approval', {
            'fields': ('approved_by', 'created_by', 'created_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(FinancialYear)
class FinancialYearAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('start_date', 'end_date')

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'start_date', 'end_date', 'financial_year', 'total_revenue', 'total_expenses', 'net_profit')
    list_filter = ('report_type', 'financial_year', 'generated_at')
    search_fields = ('report_type', 'financial_year__start_date', 'financial_year__end_date')
    readonly_fields = ('generated_at', 'generated_by')

    fieldsets = (
        (None, {
            'fields': ('report_type', 'start_date', 'end_date', 'financial_year')
        }),
        ('Financial Summary', {
            'fields': ('total_revenue', 'total_expenses', 'net_profit', 'total_gst_collected', 'total_tds_deducted')
        }),
        ('Report Details', {
            'fields': ('report_file', 'generated_by', 'generated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)
