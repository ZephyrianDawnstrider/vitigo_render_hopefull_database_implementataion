# phototherapy_management/views.py

# Standard library imports
import logging

# Third-party imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

# Local application imports
from phototherapy_management.models import PatientRFIDCard, PhototherapyPlan, PhototherapySession
from phototherapy_management.utils import get_template_path
from error_handling.views import handler500, handler403
from access_control.permissions import PermissionManager

# Logger configuration
logger = logging.getLogger(__name__)
User = get_user_model()

class RFIDDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get current datetime for comparisons
            now = timezone.now()

            # Get all RFID cards with related data
            rfid_cards = PatientRFIDCard.objects.select_related(
                'patient'
            ).annotate(
                sessions_count=Count('patient__phototherapy_plans__sessions',
                    filter=Q(patient__phototherapy_plans__sessions__status='COMPLETED')),
                active_plans=Count('patient__phototherapy_plans',
                    filter=Q(patient__phototherapy_plans__is_active=True))
            ).order_by('-is_active', '-assigned_date')

            # Calculate statistics
            card_stats = {
                'total': rfid_cards.count(),
                'active': rfid_cards.filter(is_active=True, expires_at__gt=now).count(),
                'expiring_soon': rfid_cards.filter(
                    is_active=True,
                    expires_at__range=[now, now + timezone.timedelta(days=30)]
                ).count(),
                'expired': rfid_cards.filter(expires_at__lte=now).count(),
            }

            # Get recent activities
            recent_sessions = PhototherapySession.objects.select_related(
                'plan__patient'
            ).filter(
                rfid_entry_time__isnull=False
            ).order_by('-rfid_entry_time')[:10]

            # Get all patients with PATIENT role
            patients = User.objects.filter(
                role__name='PATIENT',
                is_active=True
            ).order_by('first_name', 'last_name')

            context = {
                'rfid_cards': rfid_cards,
                'stats': card_stats,
                'recent_sessions': recent_sessions,
                'patients': patients,  # Add patients to context
                'now': now,  # Add current datetime for template comparisons
            }

            template_path = get_template_path(
                'rfid/rfid_dashboard.html',
                request.user.role,
                'phototherapy_management'
            )
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in RFID dashboard view: {str(e)}")
            messages.error(request, "An error occurred while loading RFID card data")
            return handler500(request, exception=str(e))

class RFIDCardIssueView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            # Get form data
            patient_id = request.POST.get('patient')
            card_number = request.POST.get('card_number')
            expiry_date = request.POST.get('expiry_date')
            notes = request.POST.get('notes', '')

            # Basic validation
            if not all([patient_id, card_number, expiry_date]):
                messages.error(request, "Please provide all required fields")
                return redirect('rfid_dashboard')

            # Convert expiry date to datetime
            expiry_datetime = timezone.datetime.strptime(expiry_date, '%Y-%m-%d')
            expiry_datetime = timezone.make_aware(expiry_datetime)

            # Get patient
            try:
                patient = User.objects.get(id=patient_id, role__name='PATIENT')
            except User.DoesNotExist:
                messages.error(request, "Selected patient not found")
                return redirect('rfid_dashboard')

            # Check if card number already exists
            if PatientRFIDCard.objects.filter(card_number=card_number).exists():
                messages.error(request, "This card number is already in use")
                return redirect('rfid_dashboard')

            # Create new RFID card
            PatientRFIDCard.objects.create(
                patient=patient,
                card_number=card_number,
                expires_at=expiry_datetime,
                notes=notes,
                is_active=True
            )

            messages.success(request, f"RFID card successfully issued to {patient.get_full_name()}")
            logger.info(f"RFID card {card_number} issued to patient {patient_id} by user {request.user.id}")

        except Exception as e:
            logger.error(f"Error issuing RFID card: {str(e)}")
            messages.error(request, "An error occurred while issuing the RFID card")

        return redirect('rfid_dashboard')

@method_decorator(csrf_protect, name='dispatch')
class RFIDCardEditView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_modify(request.user, 'phototherapy_management'):
            messages.error(request, "You don't have permission to edit RFID cards")
            return handler403(request)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        try:
            card = get_object_or_404(PatientRFIDCard, pk=pk)
            
            # Update fields
            card.card_number = request.POST.get('card_number')
            card.is_active = request.POST.get('is_active') == 'on'
            
            # Convert and validate expiry date
            expiry_date = request.POST.get('expiry_date')
            if expiry_date:
                expiry_datetime = timezone.datetime.strptime(expiry_date, '%Y-%m-%d')
                card.expires_at = timezone.make_aware(expiry_datetime)
            
            card.notes = request.POST.get('notes', '')
            card.save()
            
            messages.success(request, "RFID card updated successfully")
            logger.info(f"RFID card {card.id} updated by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating RFID card: {str(e)}")
            messages.error(request, "Error updating RFID card")
            
        return redirect('rfid_dashboard')