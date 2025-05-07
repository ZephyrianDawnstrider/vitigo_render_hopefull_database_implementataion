# settings/views.py

import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import PermissionDenied

from settings.models import SettingCategory, SettingDefinition, Setting, SystemConfiguration
from settings.forms import (
    SettingCategoryForm, SettingDefinitionForm, 
    SystemConfigurationForm, SettingValueForm
)
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class CoreSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Core Settings")
                return handler403(request, exception="Access Denied")

            # Get all categories with their settings
            categories = SettingCategory.objects.filter(is_active=True).order_by('order')
            
            # Get or create system configuration
            system_config, created = SystemConfiguration.objects.get_or_create()
            system_form = SystemConfigurationForm(instance=system_config)

            # Initialize forms
            category_form = SettingCategoryForm()
            definition_form = SettingDefinitionForm()

            # Prepare settings data
            settings_data = []
            for category in categories:
                definitions = SettingDefinition.objects.filter(
                    category=category,
                    is_active=True
                ).order_by('order')
                
                settings_list = []
                for definition in definitions:
                    setting, created = Setting.objects.get_or_create(
                        definition=definition,
                        defaults={'created_by': request.user}
                    )
                    form = SettingValueForm(instance=setting)
                    settings_list.append({
                        'definition': definition,
                        'setting': setting,
                        'form': form
                    })

                settings_data.append({
                    'category': category,
                    'settings': settings_list
                })

            context = {
                'categories': categories,
                'settings_data': settings_data,
                'system_form': system_form,
                'category_form': category_form,
                'definition_form': definition_form,
                'form_errors': {},  # Add dict to store form errors
            }

            # Store any form errors from session
            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')
                logger.warning(f"Form errors found: {context['form_errors']}")

            template_path = get_template_path('core/core_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in CoreSettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify settings")

            action = request.POST.get('action')

            if action == 'update_system_config':
                return self.handle_system_config(request)
            elif action == 'add_category':
                return self.handle_category_creation(request)
            elif action == 'add_definition':
                return self.handle_definition_creation(request)
            elif action == 'update_setting':
                return self.handle_setting_update(request)
            else:
                messages.error(request, "Invalid action specified")
                return redirect('settings:core_settings')

        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard')
        except Exception as e:
            logger.error(f"Error in CoreSettingsView POST: {str(e)}")
            messages.error(request, "An error occurred while saving settings")
            return redirect('settings:core_settings')

    def handle_system_config(self, request):
        try:
            config = SystemConfiguration.objects.first()
            if not config:
                config = SystemConfiguration()
                # Set some basic defaults
                config.site_name = "Your Site Name"
                config.site_url = "http://localhost:8000"
                config.admin_email = "admin@example.com"
                config.save()  # This will trigger the default JSON fields

            form = SystemConfigurationForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, "System configuration updated successfully")
                logger.info(f"System configuration updated by user {request.user.id}")
            else:
                logger.warning(f"Invalid system config data: {form.errors}")
                request.session['form_errors'] = {'system_form': form.errors}
                messages.error(request, "Please correct the errors below")
        except Exception as e:
            logger.error(f"Error updating system config: {str(e)}", exc_info=True)
            messages.error(request, "Error updating system configuration")
        return redirect('settings:core_settings')

    def handle_category_creation(self, request):
        try:
            form = SettingCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Category created successfully")
            else:
                messages.error(request, "Invalid category data")
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            messages.error(request, "Error creating category")
        return redirect('settings:core_settings')

    def handle_definition_creation(self, request):
        try:
            form = SettingDefinitionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Setting definition created successfully")
            else:
                messages.error(request, "Invalid setting definition data")
        except Exception as e:
            logger.error(f"Error creating definition: {str(e)}")
            messages.error(request, "Error creating setting definition")
        return redirect('settings:core_settings')

    def handle_setting_update(self, request):
        try:
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(Setting, id=setting_id)
            form = SettingValueForm(request.POST, instance=setting)
            if form.is_valid():
                setting = form.save(commit=False)
                setting.updated_by = request.user
                setting.save()
                messages.success(request, "Setting updated successfully")
            else:
                messages.error(request, "Invalid setting data")
        except Exception as e:
            logger.error(f"Error updating setting: {str(e)}")
            messages.error(request, "Error updating setting")
        return redirect('settings:core_settings')