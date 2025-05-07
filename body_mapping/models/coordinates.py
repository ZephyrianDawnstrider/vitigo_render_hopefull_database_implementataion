# body_mapping/models/coordinates.py
from django.db import models
from django.core.validators import FileExtensionValidator
from .base import BodyModel, BodyView
from .regions import BodyRegion

class BodyImage(models.Model):
    body_model = models.ForeignKey(BodyModel, on_delete=models.CASCADE, related_name='images')
    view = models.ForeignKey(BodyView, on_delete=models.PROTECT)
    image = models.ImageField(
        upload_to='body_images/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    resolution = models.CharField(max_length=20, blank=True)
    image_quality = models.PositiveSmallIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'body_mapping'
        unique_together = ['body_model', 'view']
    
    def __str__(self):
        return f"{self.body_model} - {self.view}"

class CoordinateGroup(models.Model):
    body_image = models.ForeignKey(BodyImage, on_delete=models.CASCADE, related_name='coordinate_groups')
    body_region = models.ForeignKey(BodyRegion, on_delete=models.CASCADE, related_name='coordinate_groups')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        app_label = 'body_mapping'
        unique_together = ['body_image', 'body_region']
    
    def __str__(self):
        return f"{self.name} - {self.body_region} ({self.body_image})"

class Coordinate(models.Model):
    coordinate_group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE, related_name='coordinates')
    label = models.CharField(max_length=50)
    x_coordinate = models.FloatField()
    y_coordinate = models.FloatField()
    sequence = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        app_label = 'body_mapping'
        ordering = ['sequence']
        unique_together = ['coordinate_group', 'label']
    
    def __str__(self):
        return f"{self.coordinate_group} - Point {self.label}"

class RegionMeasurement(models.Model):
    coordinate_group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE, related_name='measurements')
    name = models.CharField(max_length=100)
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    measurement_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        app_label = 'body_mapping'
    
    def __str__(self):
        return f"{self.coordinate_group.body_region} - {self.name}: {self.value}{self.unit}"
