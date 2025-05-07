from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ReportExport
from .tasks import generate_report

@receiver(post_save, sender=ReportExport)
def trigger_report_generation(sender, instance, created, **kwargs):
    """Trigger report generation when a new export is created"""
    if created and instance.status == 'PENDING':
        generate_report.delay(instance.id)
