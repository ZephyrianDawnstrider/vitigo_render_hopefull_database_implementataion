# Python Standard Library imports
import json
import logging
import mimetypes
import os
import csv
from io import StringIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Count, Q, F, Min, Max, Prefetch
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, FileResponse
from django.shortcuts import render, redirect
from django.template.defaultfilters import filesizeformat
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView
from django.contrib.auth import get_user_model
from django.db import transaction

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403
from .forms import PatientImageUploadForm, AnnotationForm
from .models import BodyPart, PatientImage, ImageComparison, ImageAnnotation, ComparisonImage
from consultation_management.models import Consultation

User = get_user_model()

# Logger configuration
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module='image_management'):
    """
    Simple template path resolver based on user role
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    return f'{role_folder}/{module}/{base_template}'

class ImageManagementView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Check module access permission
            if not PermissionManager.check_module_access(request.user, 'image_management'):
                messages.error(request, "You don't have permission to access Image Management")
                return handler403(request, exception="Access Denied")

            # Get template path
            template_path = get_template_path('image_dashboard.html', request.user.role)
            
            # Get filter parameters
            image_type = request.GET.get('image_type', '')
            body_part = request.GET.get('body_part', '')
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')
            search_query = request.GET.get('search', '')

            # Get all body parts for filter dropdown
            body_parts = BodyPart.objects.all().order_by('name')

            # Base queryset - Update the select_related fields
            patient_images = PatientImage.objects.select_related(
                'patient',  # This refers to the User model directly
                'body_part',
                'uploaded_by'
            ).order_by('-date_taken')

            # Apply filters
            if image_type:
                patient_images = patient_images.filter(image_type=image_type)
            if body_part:
                patient_images = patient_images.filter(body_part_id=body_part)
            if date_from:
                patient_images = patient_images.filter(date_taken__gte=date_from)
            if date_to:
                patient_images = patient_images.filter(date_taken__lte=date_to)
            if search_query:
                patient_images = patient_images.filter(
                    Q(patient__first_name__icontains=search_query) |
                    Q(patient__last_name__icontains=search_query) |
                    Q(body_part__name__icontains=search_query) |
                    Q(notes__icontains=search_query)
                )

            # Calculate statistics
            total_images = patient_images.count()
            recent_uploads = patient_images.filter(
                uploaded_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
            total_comparisons = ImageComparison.objects.count()
            storage_used = patient_images.aggregate(total_size=Sum('file_size'))['total_size'] or 0
            storage_used = round(storage_used / (1024 * 1024 * 1024), 2)  # Convert to GB

            # Setup pagination
            paginator = Paginator(patient_images, 12)
            page = request.GET.get('page')
            try:
                patient_images = paginator.page(page)
            except PageNotAnInteger:
                patient_images = paginator.page(1)
            except EmptyPage:
                patient_images = paginator.page(paginator.num_pages)

            # Add file size information
            for image in patient_images:
                if default_storage.exists(image.image_file.name):
                    image.file_size_formatted = filesizeformat(
                        default_storage.size(image.image_file.name)
                    )
                else:
                    image.file_size_formatted = 'N/A'

            context = {
                'body_parts': body_parts,
                'patient_images': patient_images,
                'total_images': total_images,
                'recent_uploads': recent_uploads,
                'total_comparisons': total_comparisons,
                'storage_used': storage_used,
                'paginator': paginator,
                'page_obj': patient_images,
                'current_filters': {
                    'image_type': image_type,
                    'body_part': body_part,
                    'date_from': date_from,
                    'date_to': date_to,
                    'search': search_query,
                }
            }

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in ImageManagementView: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('dashboard')

class ImageUploadView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = PatientImage
    form_class = PatientImageUploadForm
    template_name = None  # Remove default template_name
    success_url = reverse_lazy('image_management')

    def get_template_name(self):
        # Get correct template path based on user's role
        return get_template_path('image_upload.html', self.request.user.role, 'image_management')

    def test_func(self):
        # Replace get_permissions() with check_module_modify()
        return PermissionManager.check_module_modify(self.request.user, 'image_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to upload images")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Override get method to use correct template
        self.template_name = self.get_template_name()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Override post method to use correct template
        self.template_name = self.get_template_name()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            instance = form.save(commit=False)
            instance.uploaded_by = self.request.user
            instance.save()
            form.save_m2m()  # Save many-to-many relationships if any
            
            logger.info(
                f"Image uploaded successfully - Patient: {instance.patient.id}, "
                f"Uploaded by: {self.request.user.id}, "
                f"File size: {instance.file_size} bytes"
            )
            
            messages.success(self.request, 'Image uploaded successfully.')
            return redirect('image_management')
            
        except Exception as e:
            logger.error(f"Image upload failed - Error: {str(e)}", exc_info=True)
            messages.error(self.request, f'Failed to upload image: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(
            f"Invalid image upload attempt - Errors: {form.errors}, "
            f"User: {self.request.user.id}"
        )
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_name'] = self.get_template_name()
        return context

class ImageUploadConfirmationView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Replace role string check with proper permission check
        return PermissionManager.check_module_modify(self.request.user, 'image_management')

    def get(self, request):
        image_id = request.session.get('uploaded_image_id')
        if not image_id:
            return redirect('image_management')

        try:
            image = PatientImage.objects.get(id=image_id)
            # Clear the session
            del request.session['uploaded_image_id']
            
            template_path = get_template_path('image_upload_confirmation.html', request.user.role, 'image_management')
            return render(request, template_path, {'image': image})
        except PatientImage.DoesNotExist:
            return redirect('image_management')

class DownloadImageView(LoginRequiredMixin, View):
    def get(self, request, image_id):
        # Add permission check
        if not PermissionManager.check_module_access(request.user, 'image_management'):
            return HttpResponseForbidden("You don't have permission to access images")

        try:
            image = PatientImage.objects.get(id=image_id)
            
            # Check if user has permission to download the image
            if not request.user.is_staff and image.patient.user != request.user:
                return HttpResponseForbidden("You don't have permission to download this image")

            # Get the file path
            file_path = image.image_file.path
            
            # Get the original filename
            filename = os.path.basename(image.image_file.name)
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            
            # Open the file in binary mode
            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            
            # Set content disposition as attachment with original filename
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except PatientImage.DoesNotExist:
            messages.error(request, "Image not found")
            return redirect('image_management')
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}", exc_info=True)
            messages.error(request, "Error downloading image")
            return redirect('image_management')

class DeleteImageView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Replace get_permissions() with check_module_delete()
        return PermissionManager.check_module_delete(self.request.user, 'image_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to delete images")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, image_id):
        try:
            image = PatientImage.objects.get(id=image_id)
            
            # Store image details for logging
            image_details = {
                'patient': image.patient.get_full_name(),
                'file_name': image.image_file.name,
                'uploaded_by': image.uploaded_by.get_full_name() if image.uploaded_by else 'Unknown'
            }
            
            # Delete the image file from storage
            if default_storage.exists(image.image_file.name):
                default_storage.delete(image.image_file.name)
            
            # Delete the database record
            image.delete()
            
            logger.info(
                f"Image deleted successfully - Patient: {image_details['patient']}, "
                f"File: {image_details['file_name']}, "
                f"Deleted by: {request.user.get_full_name()}"
            )
            
            messages.success(request, "Image deleted successfully")
            return redirect('image_management')
            
        except PatientImage.DoesNotExist:
            messages.error(request, "Image not found")
            return redirect('image_management')
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}", exc_info=True)
            messages.error(request, f"Error deleting image: {str(e)}")
            return redirect('image_management')

class ImageDetailView(LoginRequiredMixin, View):
    def get(self, request, image_id):
        try:
            if not PermissionManager.check_module_access(request.user, 'image_management'):
                messages.error(request, "You don't have permission to view image details")
                return handler403(request, exception="Access Denied")

            template_path = get_template_path('image_detail.html', request.user.role)

            # Updated select_related to match correct relationships
            image = PatientImage.objects.select_related(
                'patient',  # Directly relates to CustomUser
                'body_part',
                'uploaded_by'
            ).get(id=image_id)

            file_size = None
            if image.image_file:
                try:
                    file_size = default_storage.size(image.image_file.name)
                except Exception:
                    file_size = None
            
            # Get all images of the same patient
            related_images = PatientImage.objects.filter(
                patient=image.patient
            ).exclude(id=image_id).order_by('-date_taken')
            
            # Get comparisons containing this image
            comparisons = ImageComparison.objects.filter(
                images=image
            ).select_related('created_by')
            
            # Get annotations for this image
            annotations = image.annotations.select_related('created_by').order_by('-created_at')
            
            # Get images from same body part
            similar_images = PatientImage.objects.filter(
                body_part=image.body_part
            ).exclude(id=image_id).order_by('-date_taken')[:5]
            
            context = {
                'image': image,
                'file_size': file_size, 
                'related_images': related_images,
                'comparisons': comparisons,
                'annotations': annotations,
                'similar_images': similar_images,
            }
            
            return render(request, template_path, context)
            
        except PatientImage.DoesNotExist:
            messages.error(request, "Image not found")
            return redirect('image_management')


class ImageExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'image_management')

    def get(self, request):
        try:
            export_format = request.GET.get('format', 'csv')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')

            # Get filtered queryset
            queryset = PatientImage.objects.select_related(
                'patient',  # Directly relates to CustomUser
                'body_part', 
                'uploaded_by'
            ).order_by('-date_taken')

            if date_from:
                queryset = queryset.filter(date_taken__gte=date_from)
            if date_to:
                queryset = queryset.filter(date_taken__lte=date_to)

            if export_format == 'csv':
                return self.export_csv(queryset)
            elif export_format == 'pdf':
                return self.export_pdf(queryset)
            else:
                messages.error(request, "Invalid export format")
                return redirect('image_management')

        except Exception as e:
            logger.error(f"Export failed: {str(e)}", exc_info=True)
            messages.error(request, f"Export failed: {str(e)}")
            return redirect('image_management')

    def export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="image_report_{timezone.now().strftime("%Y%m%d")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Image ID', 'Patient Name', 'Body Part', 'Type', 'Date Taken',
            'Upload Date', 'Uploaded By', 'Private', 'Size (bytes)',
            'Dimensions', 'Tags', 'Notes'
        ])

        for image in queryset:
            writer.writerow([
                image.id,
                image.patient.get_full_name(),  # Updated to use patient directly
                image.body_part.name if image.body_part else 'N/A',
                image.get_image_type_display(),
                image.date_taken.strftime('%Y-%m-%d'),
                image.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                image.uploaded_by.get_full_name() if image.uploaded_by else 'N/A',
                'Yes' if image.is_private else 'No',
                image.file_size or 'N/A',
                f'{image.width}x{image.height}' if image.width and image.height else 'N/A',
                ', '.join(tag.name for tag in image.tags.all()),
                image.notes[:100] + '...' if len(image.notes) > 100 else image.notes
            ])

        return response

    def export_pdf(self, queryset):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="image_report_{timezone.now().strftime("%Y%m%d")}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )

        # Title
        elements.append(Paragraph('Image Management Report', title_style))
        elements.append(Spacer(1, 20))

        # Summary statistics
        total_images = queryset.count()
        total_size = sum(image.file_size or 0 for image in queryset)
        private_count = queryset.filter(is_private=True).count()

        stats = [
            ['Total Images:', str(total_images)],
            ['Total Storage:', f'{total_size / (1024*1024):.2f} MB'],
            ['Private Images:', str(private_count)],
            ['Date Range:', f"{queryset.last().date_taken if queryset.exists() else 'N/A'} to {queryset.first().date_taken if queryset.exists() else 'N/A'}"]
        ]

        stats_table = Table(stats, colWidths=[100, 150])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

        # Image list
        data = [['Patient', 'Body Part', 'Type', 'Date Taken', 'Size', 'Private']]
        for image in queryset:
            data.append([
                image.patient.user.get_full_name(),
                image.body_part.name if image.body_part else 'N/A',
                image.get_image_type_display(),
                image.date_taken.strftime('%Y-%m-%d'),
                f'{image.file_size/1024:.1f} KB' if image.file_size else 'N/A',
                'Yes' if image.is_private else 'No'
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)

        doc.build(elements)
        return response

class ImageComparisonListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ImageComparison
    context_object_name = 'comparisons'
    paginate_by = 10
    
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'image_management')
    
    def get_template_names(self):
        return [get_template_path('image_comparison_list.html', self.request.user.role)]
    
    def get_queryset(self):
        queryset = ImageComparison.objects.select_related('created_by')\
            .prefetch_related(
                Prefetch(
                    'images',
                    queryset=PatientImage.objects.select_related('patient', 'body_part')
                )
            )\
            .annotate(image_count=Count('images'))\
            .order_by('-created_at')
            
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(created_by__first_name__icontains=search_query) |
                Q(created_by__last_name__icontains=search_query)
            )
            
        # Filter by type
        comparison_type = self.request.GET.get('type')
        if comparison_type in ['individual', 'consultation']:
            queryset = queryset.filter(comparison_type=comparison_type)
            
        # Filter by creator
        creator_id = self.request.GET.get('creator')
        if creator_id:
            queryset = queryset.filter(created_by_id=creator_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'selected_type': self.request.GET.get('type', ''),
            'selected_creator': self.request.GET.get('creator', ''),
        })
        return context
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to view image comparisons.")
        return redirect('image_management')

class ImageComparisonCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'image_management')
    
    def get_consultations(self, request):
        """Helper method to get filtered consultations with images"""
        consultations = Consultation.objects.prefetch_related(
            Prefetch(
                'patientimage_set',
                queryset=PatientImage.objects.select_related('body_part', 'patient')
            )
        ).select_related(
            'patient',
            'doctor'
        ).order_by('-scheduled_datetime')  # Changed from date_time to scheduled_datetime

        # Apply filters
        filters = Q()
        
        # Patient search
        if patient_search := request.GET.get('patient_search'):
            filters |= (
                Q(patient__first_name__icontains=patient_search) |
                Q(patient__last_name__icontains=patient_search) |
                Q(patient__email__icontains=patient_search)
            )

        # Date range filter
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                filters &= Q(scheduled_datetime__date__gte=start_date)  # Updated field name
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                filters &= Q(scheduled_datetime__date__lte=end_date)  # Updated field name
            except ValueError:
                pass

        # Doctor filter
        if doctor_id := request.GET.get('doctor'):
            filters &= Q(doctor_id=doctor_id)

        return consultations.filter(filters) if filters else consultations

    def get(self, request):
        try:
            template_path = get_template_path('image_comparison_create.html', request.user.role)
            
            # Get filtered consultations
            consultations = self.get_consultations(request)
            
            # Paginate results
            paginator = Paginator(consultations, 10)  # 10 consultations per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            # Group consultations by patient for the current page
            patients_consultations = {}
            for consultation in page_obj:
                if consultation.patient:
                    if consultation.patient not in patients_consultations:
                        patients_consultations[consultation.patient] = []
                    patients_consultations[consultation.patient].append({
                        'consultation': consultation,
                        'images': list(consultation.patientimage_set.all()),
                        'image_count': len(consultation.patientimage_set.all())
                    })

            # Get list of doctors for filter dropdown
            doctors = User.objects.filter(
                role__name='DOCTOR'
            ).select_related('doctor_profile').order_by('first_name')
            
            context = {
                'patients_consultations': patients_consultations,
                'page_obj': page_obj,
                'doctors': doctors,
                # Preserve filter values
                'patient_search': request.GET.get('patient_search', ''),
                'start_date': request.GET.get('start_date', ''),
                'end_date': request.GET.get('end_date', ''),
                'selected_doctor': request.GET.get('doctor', ''),
            }
            
            return render(request, template_path, context)
            
        except Exception as e:
            messages.error(request, f"Error loading comparison view: {str(e)}")
            return redirect('image_management')
    
    def post(self, request):
        try:
            with transaction.atomic():
                consultation_ids = request.POST.getlist('consultation_ids')
                if not consultation_ids:
                    messages.error(request, "Please select at least one consultation to compare.")
                    return redirect('comparison_create')

                # Get all images from selected consultations
                images = PatientImage.objects.filter(
                    consultation_id__in=consultation_ids
                ).select_related('consultation').order_by(
                    'consultation__scheduled_datetime',  # Changed from date_time
                    'id'
                )

                if not images.exists():
                    messages.error(request, "No images found in selected consultations.")
                    return redirect('comparison_create')
                
                # Create the comparison instance first
                comparison = ImageComparison(
                    title=request.POST.get('comparison_title', 'Image Comparison'),
                    description=request.POST.get('comparison_description', ''),
                    created_by=request.user,
                    comparison_type='consultation'
                )
                # Save it to get an ID
                comparison.save()
                
                # Now create the ComparisonImage instances
                comparison_images = []
                for index, image in enumerate(images, 1):
                    comparison_images.append(
                        ComparisonImage(
                            comparison=comparison,
                            image=image,
                            order=index
                        )
                    )
                
                # Bulk create the ComparisonImage instances
                if comparison_images:
                    ComparisonImage.objects.bulk_create(comparison_images)
                
                messages.success(request, "Image comparison created successfully!")
                return redirect('comparison_detail', pk=comparison.pk)
                
        except Exception as e:
            messages.error(request, f"Error creating comparison: {str(e)}")
            return redirect('comparison_create')
        
class ImageComparisonDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = ImageComparison
    context_object_name = 'comparison'
    
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'image_management')
    
    def get_template_names(self):
        return [get_template_path('image_comparison_detail.html', self.request.user.role)]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get ordered comparison images with their consultation info
        comparison_images = (ComparisonImage.objects
            .filter(comparison=self.object)
            .select_related('image', 'image__consultation', 'image__body_part', 'image__patient')
            .order_by('order'))
        
        # Group images by consultation date for better organization
        grouped_images = {}
        for comp_image in comparison_images:
            consultation = comp_image.image.consultation
            if consultation:
                date_key = consultation.scheduled_datetime.date()  # Changed from date_time
                if date_key not in grouped_images:
                    grouped_images[date_key] = {
                        'consultation': consultation,
                        'images': []
                    }
                grouped_images[date_key]['images'].append(comp_image.image)
        
        context['grouped_images'] = grouped_images
        return context
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to view image comparisons.")
        return redirect('image_management')
    

class Human3DModelView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'image_management')
    
    def get(self, request):
        template_path = get_template_path('human_3d_model.html', request.user.role)
        return render(request, template_path)