from django.contrib import admin
from .models import (
    Medication,
    MedicationStock,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'dosage_form', 'strength', 
                   'price', 'requires_prescription', 'is_active')
    list_filter = ('requires_prescription', 'is_active', 'dosage_form')
    search_fields = ('name', 'generic_name', 'manufacturer')
    ordering = ('name',)

@admin.register(MedicationStock)
class MedicationStockAdmin(admin.ModelAdmin):
    list_display = ('medication', 'quantity', 'reorder_level', 'last_restocked')
    search_fields = ('medication__name',)
    ordering = ('medication__name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email')
    ordering = ('name',)

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'order_date', 'status', 
                   'total_amount', 'expected_delivery_date', 'created_by')
    list_filter = ('status', 'order_date')
    search_fields = ('supplier__name', 'created_by__username')
    ordering = ('-order_date',)

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'medication', 'quantity', 'unit_price')
    search_fields = ('medication__name', 'purchase_order__supplier__name')
    ordering = ('-purchase_order__order_date',)
