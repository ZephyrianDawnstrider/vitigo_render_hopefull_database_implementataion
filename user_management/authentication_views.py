import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from error_handling.views import (
    handler400, handler401, handler403, handler404, handler500
)
from .forms import UserLoginForm

# Configure logger
logger = logging.getLogger(__name__)

class UserLoginView(View):
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        try:
            if request.user.is_authenticated:
                messages.info(request, f'You are already logged in as {request.user.email}')
                return redirect('dashboard')
            form = UserLoginForm()
            return render(request, 'user_management/login.html', {'form': form})
        except Exception as e:
            logger.error(f"Error in login GET: {str(e)}")
            messages.error(request, 'An error occurred while accessing the login page')
            return handler500(request, exception=e)

    def post(self, request):
        try:
            form = UserLoginForm(request.POST)
            if not form.is_valid():
                messages.error(request, 'Please correct the errors in the form')
                return render(request, 'user_management/login.html', {'form': form})

            email = form.cleaned_data.get('email')
            country_code = form.cleaned_data.get('country_code')
            phone = form.cleaned_data.get('phone')
            password = form.cleaned_data.get('password')

            user = None
            if email:
                # Try email authentication
                user = authenticate(request, username=email, password=password)
            elif country_code and phone:
                # Try phone authentication
                user = authenticate(
                    request,
                    username=phone,  # This can be anything as we're using kwargs
                    password=password,
                    country_code=country_code,
                    phone_number=phone
                )

            if not user:
                messages.error(request, 'Invalid credentials. Please try again.')
                return render(request, 'user_management/login.html', {'form': form})

            if not user.is_active:
                messages.warning(request, 'Your account is inactive. Please contact support.')
                return render(request, 'user_management/login.html', {'form': form})

            login(request, user)
            identifier = user.get_full_name() or (email if email else f"{country_code}{phone}")
            messages.success(
                request,
                f'Welcome back, {identifier}! You have successfully logged in.'
            )
            return redirect('dashboard')

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return render(request, 'user_management/login.html', {'form': form})

class UserLogoutView(LoginRequiredMixin, View):
    """Handle user logout with proper error handling and logging"""
    
    def get(self, request):
        try:
            user_email = request.user.email
            user_name = request.user.get_full_name() or user_email
            user_role = request.user.role
            logout(request)
            logger.info(f"User logged out: {user_email} (Role: {user_role})")
            messages.success(request, f'Goodbye, {user_name}! You have been logged out successfully.')
            return redirect('login')
        except AttributeError as e:
            messages.error(request, 'Invalid session. Please try logging in again.')
            return handler400(request, exception="Session error")
        except Exception as e:
            messages.error(request, 'An error occurred during logout.')
            return handler500(request, exception=e)