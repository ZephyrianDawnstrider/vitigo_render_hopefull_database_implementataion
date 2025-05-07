from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ItemCategory, StockItem, StockMovement, Supplier, PurchaseOrder, PurchaseOrderItem, StockAudit

@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 1
    readonly_fields = ('date',)

@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'current_quantity', 'unit', 'reorder_point', 'unit_price', 'is_active')
    list_filter = ('category', 'is_active', 'unit')
    search_fields = ('name', 'description')
    inlines = [StockMovementInline]
    actions = ['mark_for_reorder']

    def mark_for_reorder(self, request, queryset):
        for item in queryset:
            if item.current_quantity <= item.reorder_point:
                # Logic to create a purchase order or notification
                self.message_user(request, f"{item.name} has been marked for reorder.")
    mark_for_reorder.short_description = "Mark selected items for reorder"

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'movement_type', 'date', 'performed_by')
    list_filter = ('movement_type', 'date')
    search_fields = ('item__name', 'notes')
    readonly_fields = ('date',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email')

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'order_date', 'status', 'total_amount', 'created_by', 'approved_by')
    list_filter = ('status', 'order_date')
    search_fields = ('supplier__name', 'notes')
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ('order_date',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        if obj.status == 'APPROVED' and not obj.approved_by:
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(StockAudit)
class StockAuditAdmin(admin.ModelAdmin):
    list_display = ('item', 'audit_date', 'expected_quantity', 'actual_quantity', 'discrepancy', 'performed_by')
    list_filter = ('audit_date',)
    search_fields = ('item__name', 'notes')
    readonly_fields = ('audit_date',)
