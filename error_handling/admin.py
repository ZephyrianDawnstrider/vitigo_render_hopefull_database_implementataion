from django.contrib import admin
from django.utils.html import format_html
from .models import ErrorLog


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'short_message', 'user', 'url', 'method')
    list_filter = ('level', 'timestamp', 'method')
    search_fields = ('message', 'user__username', 'url')
    readonly_fields = ('timestamp', 'level', 'message', 'traceback', 'user', 'url', 'method', 'data')

    fieldsets = (
        (None, {
            'fields': ('timestamp', 'level', 'message', 'traceback')
        }),
        ('Request Information', {
            'fields': ('user', 'url', 'method', 'data'),
            'classes': ('collapse',),
        }),
    )

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

    short_message.short_description = 'Message'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


