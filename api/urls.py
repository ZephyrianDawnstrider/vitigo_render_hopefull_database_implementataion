# urls.py
from django.urls import path
from . import views
from ._views import (
    authentication as auth_views,
)

urlpatterns = [
    # Existing authentication URLs
    path('register/', auth_views.UserRegistrationAPIView.as_view(), name='api_register'),
    path('roles/', auth_views.RoleListView.as_view(), name='role-list'),
    path('assign-role/', auth_views.UserRoleAssignmentView.as_view(), name='assign-role'),

    path('login/', auth_views.UserLoginAPIView.as_view(), name='api_login'),
    path('user-info/', auth_views.UserInfoView.as_view(), name='user_info'),
    path('basic-user-info/update/', auth_views.BasicUserInfoUpdateAPIView.as_view(), name='user-update'),
    path('password-reset/', auth_views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('reset-password/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
   
    # Patient related URLs
    path('patient-info/', views.PatientInfoView.as_view(), name='patient-info'),
    path('patient/<int:user_id>/profile/', views.PatientProfileAPIView.as_view(), name='patient-profile'),
    path('patient/<int:user_id>/medical-history/', views.MedicalHistoryAPIView.as_view(), name='medical-history'),
    
    # Doctor related URLs - grouped together
    path('doctors/', views.DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:doctor_id>/', views.DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctors/specializations/', views.SpecializationListView.as_view(), name='specialization-list'),
    path('doctors/treatment-methods/', views.TreatmentMethodListView.as_view(), name='treatment-method-list'),
    path('doctors/body-areas/', views.BodyAreaListView.as_view(), name='body-area-list'),
    path('doctors/associated-conditions/', views.AssociatedConditionListView.as_view(), name='associated-condition-list'),
    path('doctors/<int:doctor_id>/timeslots/', views.DoctorAvailableTimeSlotsView.as_view(), name='doctor-timeslots'),
    path('doctors/time-slot/<int:slot_id>/', views.DoctorTimeSlotDetailView.as_view(), name='time-slot-detail'),    
    # Appointment related URLs
    path('appointments/', views.UserAppointmentsView.as_view(), name='user-appointments-list'),
    path('appointments/<int:appointment_id>/', views.UserAppointmentDetailView.as_view(), name='user-appointment-detail'),
    path('appointments/timeslots/available/', views.DoctorAvailableTimeSlotsView.as_view(), name='available-timeslots'),
    path('appointments/types/', views.AppointmentTypesView.as_view(), name='appointment-types'),
    path('appointments/priorities/', views.AppointmentPriorityView.as_view(), name='appointment-priorities'),
    path('appointments/create/', views.CreateAppointmentView.as_view(), name='create-appointment'),

    # Query related URLs
    path('queries/', views.UserQueriesView.as_view(), name='user-queries'),
    path('queries/query-tags/', views.QueryTagListView.as_view(), name='query-tag-list'),
    path('queries/priority-choices/', views.PriorityChoicesView.as_view(), name='priority-choices'),
    path('queries/source-choices/', views.SourceChoicesView.as_view(), name='source-choices'),
    path('queries/status-choices/', views.StatusChoicesView.as_view(), name='status-choices'),
    path('doctor/<int:doctor_id>/clinics/', views.DoctorClinicsAPIView.as_view(), name='doctor-clinics'),
]
