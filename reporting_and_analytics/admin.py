from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Report, ReportCategory, ReportExport

admin.site.register(ReportCategory)
admin.site.register(Report)
admin.site.register(ReportExport)