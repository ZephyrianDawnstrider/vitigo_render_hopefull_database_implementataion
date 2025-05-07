# body_mapping/models/base.py
from django.db import models

class Gender(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        app_label = 'body_mapping'
    
    def __str__(self):
        return self.name

class BodyView(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        app_label = 'body_mapping'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

class BodyModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, blank=True)
    
    class Meta:
        app_label = 'body_mapping'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.gender}"