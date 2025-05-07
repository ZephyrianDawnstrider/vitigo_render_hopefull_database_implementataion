# body_mapping/models/regions.py
from django.db import models
from .base import BodyView

class BodyRegion(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    parent_region = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='sub_regions'
    )
    applicable_views = models.ManyToManyField(BodyView)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        app_label = 'body_mapping'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_all_sub_regions(self):
        """Get all sub-regions recursively"""
        regions = list(self.sub_regions.all())
        for sub_region in self.sub_regions.all():
            regions.extend(sub_region.get_all_sub_regions())
        return regions