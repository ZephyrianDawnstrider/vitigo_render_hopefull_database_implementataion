from django.db import models
from django.contrib.auth import get_user_model

class Module(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., 'help_support'
    display_name = models.CharField(max_length=100)  # e.g., 'Help & Support'
    url_name = models.CharField(max_length=100)  # e.g., 'help_support_dashboard'
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, blank=True)  # For sidebar icons
    order = models.IntegerField(default=0)  # For sidebar ordering
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ['order', 'display_name']

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., 'ADMIN'
    display_name = models.CharField(max_length=100)  # e.g., 'Administrator'
    template_folder = models.CharField(max_length=50)  # e.g., 'admin'
    description = models.TextField(blank=True)

    def __str__(self):
        return self.display_name

class ModulePermission(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    can_access = models.BooleanField(default=False)
    can_modify = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('module', 'role')
        
    def __str__(self):
        return f"{self.role.name} - {self.module.name}"