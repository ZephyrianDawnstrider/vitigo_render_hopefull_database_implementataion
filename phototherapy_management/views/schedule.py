# Standard library imports
import logging
from datetime import timedelta, datetime

# Django imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.generic import View, CreateView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy, reverse

# Local/application imports
from access_control.permissions import PermissionManager
from error_handling.views import handler500, handler403
from phototherapy_management.models import (
    PhototherapyPlan,
    PhototherapySession,
)
from phototherapy_management.forms import ScheduleSessionForm
from phototherapy_management.utils import get_template_path
from phototherapy_management.models import ProblemReport

# Configure logging
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()

class ScheduleManagementView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get selected week from query params, default to current week
            selected_date = request.GET.get('date')
            if selected_date:
                try:
                    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
                except ValueError:
                    selected_date = timezone.now().date()
            else:
                selected_date = timezone.now().date()

            # Calculate week range
            week_start = selected_date - timedelta(days=selected_date.weekday())
            week_end = week_start + timedelta(days=6)
            today = timezone.now().date()

            # Navigation dates
            prev_week = (week_start - timedelta(days=7)).strftime('%Y-%m-%d')
            next_week = (week_start + timedelta(days=7)).strftime('%Y-%m-%d')

            # Fetch sessions for current week with optimized queries
            weekly_sessions = (PhototherapySession.objects.select_related(
                'plan__patient__patient_profile__user',
                'plan__protocol',
                'device'
            ).filter(
                scheduled_date__range=[week_start, week_end]
            ).order_by('scheduled_date', 'scheduled_time'))

            # Get today's sessions for the table view
            today_sessions = weekly_sessions.filter(scheduled_date=today)

            # Calculate statistics
            session_stats = self.calculate_session_stats(weekly_sessions, today)

            # Group sessions by date for calendar view
            time_slots = self.group_sessions_by_date(weekly_sessions)

            # Daily statistics for the week
            daily_stats = self.calculate_daily_stats(weekly_sessions)

            context = {
                'weekly_sessions': weekly_sessions,
                'today_sessions': today_sessions,
                'daily_stats': daily_stats,
                'session_stats': session_stats,
                'time_slots': time_slots,
                'week_start': week_start,
                'week_end': week_end,
                'today': today,
                'prev_week': prev_week,
                'next_week': next_week,
                'selected_date': selected_date,
            }

            template_path = get_template_path(
                'schedule_management.html',
                request.user.role,
                'phototherapy_management'
            )

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in schedule management view: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the schedule data.")
            return handler500(request, exception=str(e))

    def calculate_session_stats(self, weekly_sessions, today):
        """Calculate statistics for the dashboard cards"""
        try:
            today_sessions = weekly_sessions.filter(scheduled_date=today)
            today_completed = today_sessions.filter(status='COMPLETED').count()
            today_total = today_sessions.count()
            
            return {
                'today_total': today_total,
                'today_completed': today_completed,
                'week_total': weekly_sessions.count(),
                'pending_confirmation': weekly_sessions.filter(
                    status='SCHEDULED'
                ).count(),
                'completion_rate': (
                    (today_completed / today_total * 100) 
                    if today_total > 0 else 0
                )
            }
        except Exception as e:
            logger.error(f"Error calculating session stats: {str(e)}")
            return {
                'today_total': 0,
                'today_completed': 0,
                'week_total': 0,
                'pending_confirmation': 0,
                'completion_rate': 0
            }

    def calculate_daily_stats(self, weekly_sessions):
        """Calculate statistics for each day of the week"""
        try:
            return weekly_sessions.values('scheduled_date').annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
                missed=Count('id', filter=Q(status='MISSED')),
                cancelled=Count('id', filter=Q(status='CANCELLED')),
            ).order_by('scheduled_date')
        except Exception as e:
            logger.error(f"Error calculating daily stats: {str(e)}")
            return []

    def group_sessions_by_date(self, sessions):
        """Group sessions by date for calendar view"""
        try:
            time_slots = {}
            for session in sessions:
                slot_key = session.scheduled_date.strftime('%Y-%m-%d')
                if slot_key not in time_slots:
                    time_slots[slot_key] = []
                # Add session with calculated properties
                session_data = {
                    'id': session.id,
                    'scheduled_time': session.scheduled_time,
                    'status': session.status,
                    'plan': session.plan,
                    'device': session.device,
                    'patient_name': (
                        session.plan.patient.patient_profile.user.get_full_name()
                        if hasattr(session.plan.patient, 'patient_profile')
                        else "Unknown Patient"
                    ),
                    'protocol_name': (
                        session.plan.protocol.name 
                        if session.plan.protocol 
                        else "No Protocol"
                    ),
                    'session_number': session.session_number,
                }
                time_slots[slot_key].append(session_data)
            return time_slots
        except Exception as e:
            logger.error(f"Error grouping sessions by date: {str(e)}")
            return {}

    def handle_session_action(self, request, session_id, action):
        """Handle session actions like start, cancel, etc."""
        try:
            session = PhototherapySession.objects.get(id=session_id)
            
            if action == 'start':
                session.status = 'IN_PROGRESS'
                session.actual_start_time = timezone.now()
            elif action == 'cancel':
                session.status = 'CANCELLED'
            elif action == 'complete':
                session.status = 'COMPLETED'
                session.actual_end_time = timezone.now()
            
            session.save()
            return True, "Session updated successfully"
            
        except PhototherapySession.DoesNotExist:
            return False, "Session not found"
        except Exception as e:
            logger.error(f"Error handling session action: {str(e)}")
            return False, "Error updating session"
        

class ScheduleSessionView(LoginRequiredMixin, CreateView):
    model = PhototherapySession
    form_class = ScheduleSessionForm
    success_url = reverse_lazy('schedule_management')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_modify(request.user, 'phototherapy_management'):
                logger.warning(
                    f"Access denied to session scheduling for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to schedule sessions")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in schedule session dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def form_valid(self, form):
        try:
            # Set session number based on existing sessions
            plan = form.cleaned_data['plan']
            session_number = plan.sessions.count() + 1
            form.instance.session_number = session_number
            
            # Set default status
            form.instance.status = 'SCHEDULED'
            
            # Ensure administered_by is set
            if not form.instance.administered_by:
                form.instance.administered_by = self.request.user
            
            messages.success(self.request, "Session scheduled successfully")
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            messages.error(self.request, "Failed to schedule session")
            return super().form_invalid(form)

    def get_template_names(self):
        try:
            return [get_template_path(
                'schedule_session.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_schedule_session.html']


class SessionDetailView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        try:
            # Get session with related data
            session = PhototherapySession.objects.select_related(
                'plan__patient__patient_profile__user',
                'plan__protocol',
                'device',
                'administered_by'
            ).get(id=session_id)

            context = {
                'session': session,
                'problem_reports': session.problem_reports.all()
            }

            template_path = get_template_path(
                'session_detail.html',
                request.user.role,
                'phototherapy_management'
            )

            return render(request, template_path, context)

        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
            return redirect('schedule_management')
        except Exception as e:
            logger.error(f"Error viewing session details: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading session details")
            return redirect('schedule_management')


class AddSessionReportView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        try:
            session = PhototherapySession.objects.get(id=session_id)
            
            # Create the problem report
            problem_report = ProblemReport.objects.create(
                session=session,
                reported_by=request.user,
                problem_description=request.POST.get('problem_description'),
                severity=request.POST.get('severity'),
                action_taken=request.POST.get('action_taken')
            )
            
            # Update session's problem severity and side effects
            session.problem_severity = request.POST.get('severity')
            session.side_effects = request.POST.get('side_effects', '')
            session.save()
            
            messages.success(request, "Problem report added successfully")
            
        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
        except Exception as e:
            logger.error(f"Error adding problem report: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while adding the problem report")
        
        return redirect('session_detail', session_id=session_id)


class UpdateSessionNotesView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        try:
            session = PhototherapySession.objects.get(id=session_id)
            session.staff_notes = request.POST.get('staff_notes', '')
            session.save()
            
            messages.success(request, "Staff notes updated successfully")
            
        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
        except Exception as e:
            logger.error(f"Error updating staff notes: {str(e)}")
            messages.error(request, "An error occurred while updating staff notes")
        
        return redirect('session_detail', session_id=session_id)


class UpdateRFIDTrackingView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        try:
            session = PhototherapySession.objects.get(id=session_id)
            
            # Get entry and exit times from form
            entry_date = request.POST.get('entry_date')
            entry_time = request.POST.get('entry_time')
            exit_date = request.POST.get('exit_date')
            exit_time = request.POST.get('exit_time')
            
            # Combine date and time strings
            if entry_date and entry_time:
                entry_datetime = f"{entry_date} {entry_time}"
                session.rfid_entry_time = timezone.datetime.strptime(entry_datetime, '%Y-%m-%d %H:%M')
            
            if exit_date and exit_time:
                exit_datetime = f"{exit_date} {exit_time}"
                session.rfid_exit_time = timezone.datetime.strptime(exit_datetime, '%Y-%m-%d %H:%M')
            
            session.save()
            messages.success(request, "RFID tracking times updated successfully")
            
        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
        except ValueError as e:
            logger.error(f"Error parsing datetime: {str(e)}")
            messages.error(request, "Invalid date/time format")
        except Exception as e:
            logger.error(f"Error updating RFID tracking: {str(e)}")
            messages.error(request, "An error occurred while updating RFID tracking")
        
        return redirect('session_detail', session_id=session_id)


class UpdateSessionStatusView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        try:
            session = PhototherapySession.objects.get(id=session_id)
            status = request.POST.get('status')
            
            # Update status and related fields
            session.status = status
            
            # Handle duration for any status update
            duration = request.POST.get('duration_seconds')
            if duration:
                try:
                    session.duration_seconds = int(duration)
                except ValueError:
                    messages.error(request, "Invalid duration value")
                    return redirect('session_detail', session_id=session_id)
            
            # Set completion fields if status is COMPLETED
            if status == 'COMPLETED':
                session.actual_date = timezone.now().date()
                session.administered_by = request.user
            
            session.save()
            messages.success(request, f"Session status updated to {session.get_status_display()}")
            
        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
        except Exception as e:
            logger.error(f"Error updating session status: {str(e)}")
            messages.error(request, "An error occurred while updating session status")
        
        return redirect('session_detail', session_id=session_id)


class SessionListView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            # Get filter parameters from request
            filter_status = request.GET.get('status', '')
            filter_start_date = request.GET.get('start_date', '')
            filter_end_date = request.GET.get('end_date', '')
            search_query = request.GET.get('search', '')

            # Base queryset with optimized joins
            sessions = PhototherapySession.objects.select_related(
                'plan__patient',
                'plan__protocol',
                'device',
                'administered_by'
            ).order_by('-scheduled_date', '-scheduled_time')

            # Apply filters
            if filter_status:
                sessions = sessions.filter(status=filter_status)
            
            if filter_start_date:
                sessions = sessions.filter(scheduled_date__gte=filter_start_date)
            
            if filter_end_date:
                sessions = sessions.filter(scheduled_date__lte=filter_end_date)
            
            if search_query:
                sessions = sessions.filter(
                    Q(plan__patient__first_name__icontains=search_query) |
                    Q(plan__patient__last_name__icontains=search_query) |
                    Q(plan__protocol__name__icontains=search_query)
                )

            # Calculate statistics
            total_count = sessions.count()
            completed_count = sessions.filter(status='COMPLETED').count()
            missed_count = sessions.filter(status='MISSED').count()

            # Prepare status choices for the filter dropdown
            status_choices = [
                ('SCHEDULED', 'Scheduled'),
                ('COMPLETED', 'Completed'),
                ('MISSED', 'Missed'),
                ('CANCELLED', 'Cancelled')
            ]

            context = {
                'sessions': sessions,
                'total_count': total_count,
                'completed_count': completed_count,
                'missed_count': missed_count,
                'status_choices': status_choices,
                'filter_status': filter_status,
                'filter_start_date': filter_start_date,
                'filter_end_date': filter_end_date,
                'search_query': search_query
            }

            template_path = get_template_path(
                'session_list.html',
                request.user.role,
                'phototherapy_management'
            )

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in session list view: {str(e)}", exc_info=True)
            messages.error(
                request,
                "An error occurred while loading the sessions list."
            )
            return redirect('schedule_management')

    def post(self, request):
        try:
            # Handle bulk actions if implemented
            action = request.POST.get('action')
            selected_sessions = request.POST.getlist('selected_sessions')

            if action and selected_sessions:
                if action == 'cancel':
                    PhototherapySession.objects.filter(
                        id__in=selected_sessions
                    ).update(status='CANCELLED')
                    messages.success(request, "Selected sessions cancelled successfully")
                elif action == 'reschedule':
                    # Implement rescheduling logic if needed
                    pass

            return redirect('session_list')

        except Exception as e:
            logger.error(f"Error processing bulk action: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while processing the request")
            return redirect('session_list')


class UpdateSessionRemarksView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        try:
            session = PhototherapySession.objects.get(id=session_id)
            session.remarks = request.POST.get('remarks', '')
            session.save()
            
            messages.success(request, "Session remarks updated successfully")
            
        except PhototherapySession.DoesNotExist:
            messages.error(request, "Session not found")
        except Exception as e:
            logger.error(f"Error updating session remarks: {str(e)}")
            messages.error(request, "An error occurred while updating remarks")
        
        return redirect('session_detail', session_id=session_id)