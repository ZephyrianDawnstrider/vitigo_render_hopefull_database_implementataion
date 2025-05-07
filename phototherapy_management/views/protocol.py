# Standard library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import View
from django.urls import reverse

# Local/application imports
from error_handling.views import handler500
from phototherapy_management.models import (
    PhototherapyPlan,
    PhototherapyProtocol,
    PhototherapyType,
)
from phototherapy_management.utils import get_template_path
from phototherapy_management.forms import ProtocolForm

# Configure logging
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()

class ProtocolManagementView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Fetch protocols with related data
            protocols = PhototherapyProtocol.objects.select_related(
                'phototherapy_type',
                'created_by'
            ).annotate(
                active_plans=Count('phototherapyplan'),
                avg_improvement=Avg('phototherapyplan__progress_records__improvement_percentage')
            ).order_by('-is_active', 'name')

            # Get protocol statistics
            protocol_stats = {
                'total': protocols.count(),
                'active': protocols.filter(is_active=True).count(),
                'types': PhototherapyType.objects.count(),
                'plans_using_protocols': PhototherapyPlan.objects.filter(
                    protocol__in=protocols,
                    is_active=True
                ).count()
            }

            # Group protocols by type
            protocols_by_type = {}
            for protocol in protocols:
                type_name = protocol.phototherapy_type.name
                if type_name not in protocols_by_type:
                    protocols_by_type[type_name] = []
                protocols_by_type[type_name].append(protocol)

            context = {
                'protocols': protocols,
                'protocols_by_type': protocols_by_type,
                'stats': protocol_stats,
                'phototherapy_types': PhototherapyType.objects.all(),
            }

            template_path = get_template_path(
                'protocol_management.html', 
                request.user.role, 
                'phototherapy_management'
            )
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in protocol management view: {str(e)}")
            messages.error(request, "An error occurred while loading protocol data")
            return handler500(request, exception=str(e))
        

class AddProtocolView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            form = ProtocolForm()
            return self.render_protocol_form(request, form)
        except Exception as e:
            logger.error(f"Error in add protocol view GET: {str(e)}")
            messages.error(request, "An error occurred while loading the form")
            return redirect('protocol_management')

    def post(self, request):
        try:
            form = ProtocolForm(request.POST)
            if form.is_valid():
                # Log successful validation
                logger.info("Protocol form validation successful")
                protocol = form.save(commit=False)
                protocol.created_by = request.user
                protocol.save()
                messages.success(request, f"Protocol '{protocol.name}' created successfully")
                return redirect('protocol_management')
            else:
                # Log validation errors and add them to messages
                logger.warning(f"Protocol form validation failed: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            messages.error(request, error)
                        else:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                return self.render_protocol_form(request, form)
        except Exception as e:
            logger.error(f"Error in add protocol view POST: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
            return self.render_protocol_form(request, form)

    def render_protocol_form(self, request, form):
        template_path = get_template_path('add_protocol.html', request.user.role, 'phototherapy_management')
        return render(request, template_path, {'form': form})
        

class EditProtocolView(LoginRequiredMixin, View):
    def get(self, request, protocol_id):
        try:
            protocol = get_object_or_404(
                PhototherapyProtocol.objects.select_related('phototherapy_type', 'created_by')
                .annotate(active_plans=Count('phototherapyplan')),
                id=protocol_id
            )
            
            # Check if protocol is in use
            is_in_use = protocol.active_plans > 0
            
            form = ProtocolForm(instance=protocol)
            
            context = {
                'form': form,
                'protocol': protocol,
                'is_in_use': is_in_use
            }
            
            template_path = get_template_path(
                'edit_protocol.html',
                request.user.role,
                'phototherapy_management'
            )
            return render(request, template_path, context)
            
        except Exception as e:
            logger.error(f"Error in edit protocol view GET: {str(e)}")
            messages.error(request, "An error occurred while loading the protocol")
            return redirect('protocol_management')

    def post(self, request, protocol_id):
        try:
            protocol = get_object_or_404(PhototherapyProtocol, id=protocol_id)
            form = ProtocolForm(request.POST, instance=protocol)
            
            if form.is_valid():
                updated_protocol = form.save()
                messages.success(request, f"Protocol '{updated_protocol.name}' updated successfully")
                return redirect('protocol_management')
            
            context = {
                'form': form,
                'protocol': protocol,
                'is_in_use': PhototherapyPlan.objects.filter(protocol=protocol, is_active=True).exists()
            }
            
            template_path = get_template_path(
                'edit_protocol.html',
                request.user.role,
                'phototherapy_management'
            )
            return render(request, template_path, context)
            
        except Exception as e:
            logger.error(f"Error in edit protocol view POST: {str(e)}")
            messages.error(request, "An error occurred while updating the protocol")
            return redirect('protocol_management')


class ProtocolDetailView(LoginRequiredMixin, View):
    def get(self, request, protocol_id):
        try:
            # Get protocol with related data and statistics
            protocol = get_object_or_404(
                PhototherapyProtocol.objects.select_related(
                    'phototherapy_type',
                    'created_by'
                ).annotate(
                    active_plans=Count('phototherapyplan', filter=models.Q(phototherapyplan__is_active=True)),
                    total_plans=Count('phototherapyplan'),
                    avg_improvement=Avg('phototherapyplan__progress_records__improvement_percentage'),
                    total_sessions=Count('phototherapyplan__sessions'),
                    completed_sessions=Count(
                        'phototherapyplan__sessions',
                        filter=models.Q(phototherapyplan__sessions__status='COMPLETED')
                    )
                ),
                id=protocol_id
            )

            # Get recent plans using this protocol
            recent_plans = PhototherapyPlan.objects.filter(
                protocol=protocol
            ).select_related('patient').order_by('-created_at')[:5]

            # Calculate success metrics
            success_metrics = {
                'completion_rate': (protocol.completed_sessions / protocol.total_sessions * 100) if protocol.total_sessions else 0,
                'active_plans': protocol.active_plans,
                'total_plans': protocol.total_plans,
                'avg_improvement': protocol.avg_improvement or 0
            }

            context = {
                'protocol': protocol,
                'recent_plans': recent_plans,
                'success_metrics': success_metrics,
            }

            template_path = get_template_path(
                'protocol_detail.html',
                request.user.role,
                'phototherapy_management'
            )
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in protocol detail view: {str(e)}")
            messages.error(request, "An error occurred while loading protocol details")
            return redirect('protocol_management')


class ActivateProtocolView(LoginRequiredMixin, View):
    def post(self, request, protocol_id):
        try:
            protocol = get_object_or_404(PhototherapyProtocol, id=protocol_id)
            protocol.is_active = True
            protocol.save()
            
            messages.success(request, f"Protocol '{protocol.name}' has been activated successfully")
            return redirect(reverse('protocol_detail', kwargs={'protocol_id': protocol_id}))
            
        except Exception as e:
            logger.error(f"Error activating protocol: {str(e)}")
            messages.error(request, "An error occurred while activating the protocol")
            return redirect('protocol_management')

class DeactivateProtocolView(LoginRequiredMixin, View):
    def post(self, request, protocol_id):
        try:
            protocol = get_object_or_404(PhototherapyProtocol, id=protocol_id)
            
            # Check if protocol is in use
            active_plans = PhototherapyPlan.objects.filter(
                protocol=protocol,
                is_active=True
            ).count()
            
            if active_plans > 0:
                messages.error(
                    request,
                    f"Cannot deactivate protocol - it is currently being used in {active_plans} active treatment plans"
                )
                return redirect(reverse('protocol_detail', kwargs={'protocol_id': protocol_id}))
            
            protocol.is_active = False
            protocol.save()
            
            messages.success(request, f"Protocol '{protocol.name}' has been deactivated successfully")
            return redirect(reverse('protocol_detail', kwargs={'protocol_id': protocol_id}))
            
        except Exception as e:
            logger.error(f"Error deactivating protocol: {str(e)}")
            messages.error(request, "An error occurred while deactivating the protocol")
            return redirect('protocol_management')