from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from appointment_management.models import Appointment

@require_POST
def update_session_duration(request, session_id):
    appointment = get_object_or_404(Appointment, id=session_id)
    try:
        new_duration = int(request.POST.get('duration'))
        # Assuming Appointment model has a duration field; if not, adjust accordingly
        appointment.duration = new_duration
        appointment.save()
        return JsonResponse({'status': 'success', 'message': 'Session duration updated.'})
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Invalid duration value.')

@require_POST
def update_session_status(request, session_id):
    appointment = get_object_or_404(Appointment, id=session_id)
    new_status = request.POST.get('status')
    if new_status not in [choice[0] for choice in Appointment.STATUS_CHOICES]:
        return HttpResponseBadRequest('Invalid status value.')
    appointment.status = new_status
    appointment.save()
    return JsonResponse({'status': 'success', 'message': 'Session status updated.'})