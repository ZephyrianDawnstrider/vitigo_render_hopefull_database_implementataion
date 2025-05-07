from celery import shared_task
from django.core.files import File
from .models import ReportExport
from .services.report_generators import ReportGeneratorFactory
import os

@shared_task
def generate_report(export_id):
    try:
        # Get the export instance
        export = ReportExport.objects.get(id=export_id)
        
        # Update status to in progress
        export.status = 'IN_PROGRESS'
        export.save()

        # Get appropriate generator
        generator = ReportGeneratorFactory.get_generator(
            export.report.category.name,
            export.report.name
        )

        if generator:
            # Generate the report
            temp_file_path = generator(export.start_date, export.end_date)
            
            # Save the generated file to export
            with open(temp_file_path, 'rb') as f:
                export.export_file.save(
                    f'report_{export.id}.xlsx',
                    File(f),
                    save=True
                )
            
            # Update status to completed
            export.status = 'COMPLETED'
            export.save()

            # Clean up temp file
            os.remove(temp_file_path)
        else:
            raise ValueError("No generator found for this report type")

    except Exception as e:
        if export:
            export.status = 'FAILED'
            export.error_message = str(e)
            export.save()
        raise
