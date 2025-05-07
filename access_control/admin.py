from django.contrib import admin
from .models import Module, Role, ModulePermission

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'url_name', 'order', 'is_active')
    search_fields = ('name', 'display_name')
    list_filter = ('is_active',)
    ordering = ('order', 'display_name')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'template_folder')
    search_fields = ('name', 'display_name')

@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module', 'can_access', 'can_modify', 'updated_at')
    list_filter = ('role', 'module', 'can_access', 'can_modify')
    search_fields = ('role__name', 'module__name')
    date_hierarchy = 'updated_at'