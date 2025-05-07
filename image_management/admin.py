from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import BodyPart, ImageTag, PatientImage, ImageComparison, ComparisonImage, ImageAnnotation

admin.site.register(BodyPart)
admin.site.register(ImageTag)
admin.site.register(ComparisonImage)
admin.site.register(ImageAnnotation)
admin.site.register(ImageComparison)
admin.site.register(PatientImage)
