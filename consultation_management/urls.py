# URLs configuration (add to urls.py)
from django.urls import path
from . import views, export_views, prescription_views

urlpatterns = [
    path('', views.ConsultationDashboardView.as_view(), name='consultation_dashboard'),
    path('patient/', views.PatientConsultationDashboardView.as_view(), name='patient_consultation_dashboard'),
    path('create/', views.ConsultationCreateView.as_view(), name='consultation_create'),
    path('patients/create/', views.PatientsConsultationCreateView.as_view(), name='patients_consultation_create'),
    path('<int:pk>/', views.ConsultationDetailView.as_view(), name='consultation_detail'),
    path('delete/<int:consultation_id>/', views.ConsultationDeleteView.as_view(), name='consultation_delete'),
    
    path('update-status/<int:pk>/', views.ConsultationStatusUpdateView.as_view(), 
    name='consultation_status_update'),
    path('staff-instructions/<int:pk>/', views.StaffInstructionsUpdateView.as_view(), name='staff_instructions_update'),
    
    path('clinical-info/<int:pk>/update/', views.ClinicalInformationUpdateView.as_view(), name='update_clinical_info'),
    
    path('prescriptions/', prescription_views.PrescriptionDashboardView.as_view(), name='prescription_dashboard'),
    path('prescription/create/<int:consultation_id>/', prescription_views.PrescriptionCreateView.as_view(), name='create_prescription'),
    
    path('prescription/use-template/<int:consultation_id>/<int:template_id>/', 
         prescription_views.UsePrescriptionTemplateView.as_view(), 
         name='use_prescription_template'),
    path('prescription/edit/<int:consultation_id>/<int:prescription_id>/',
         prescription_views.PrescriptionEditView.as_view(),
         name='edit_prescription'),
    path('prescription/delete/<int:consultation_id>/<int:prescription_id>/',
         export_views.PrescriptionDeleteView.as_view(),
         name='delete_prescription'),
    path('prescriptions/template/create/', prescription_views.PrescriptionTemplateCreateView.as_view(), name='create_prescription_template'),
    path('prescriptions/template/<int:pk>/edit/', prescription_views.PrescriptionTemplateEditView.as_view(), name='edit_prescription_template'),
    path('prescriptions/template/<int:pk>/delete/', prescription_views.PrescriptionTemplateDeleteView.as_view(), name='delete_prescription_template'),
    path('export/', export_views.ConsultationExportView.as_view(), name='consultation_export'),
    path('prescription/<int:prescription_id>/export/', export_views.PrescriptionExportView.as_view(), name='export_prescription'),
    path('prescriptions/export/', export_views.PrescriptionDashboardExportView.as_view(), name='export_prescription_dashboard'),
    path('doctor-notes/<int:pk>/update/', views.DoctorNotesUpdateView.as_view(), name='update_doctor_notes'),
    path('consultation/<int:pk>/export/', 
         export_views.ConsultationDetailExportView.as_view(), 
         name='export_consultation_detail'),
    path('patient-instructions/<int:pk>/update/', 
         views.PatientInstructionsUpdateView.as_view(), 
         name='update_patient_instructions'),
    path('treatment-plan/<int:pk>/update/', 
         views.TreatmentPlanUpdateView.as_view(), 
         name='update_treatment_plan'),
    path('edit/<int:pk>/', views.ConsultationEditView.as_view(), name='consultation_edit'),
    path('doctor-clinics/', views.DoctorClinicsView.as_view(), name='doctor_clinics'),

    # API endpoints for doctor centers, available dates, and timeslots
    path('api/doctor-centers/', views.get_doctor_centers, name='get_doctor_centers'),
    path('api/doctor-available-dates/', views.get_doctor_available_dates, name='get_doctor_available_dates'),
    path('api/doctor-timeslots/', views.get_doctor_timeslots, name='get_doctor_timeslots'),
]
