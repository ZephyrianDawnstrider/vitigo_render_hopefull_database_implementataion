from django import template
from access_control.permissions import PermissionManager

register = template.Library()

@register.filter(name='has_module_access')
def has_module_access(user, module_name):
    return PermissionManager.check_module_access(user, module_name)
