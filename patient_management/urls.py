from django.urls import path
from . import views
from . import export_views

urlpatterns = [
    path('', views.PatientListView.as_view(), name='patient_list'),
    path('<int:user_id>/detail/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('register/', views.PatientRegistrationView.as_view(), name='patient_registration'),
    path('<int:user_id>/create-profile/', views.CreatePatientProfileView.as_view(), name='create_patient_profile'),
    path('<int:user_id>/edit-profile/', views.EditPatientProfileView.as_view(), name='edit_patient_profile'),
    path('<int:user_id>/deactivate/', views.DeactivatePatientView.as_view(), name='deactivate_patient'),
    path('<int:user_id>/activate/', views.ActivatePatientView.as_view(), name='activate_patient'),
    path('<int:user_id>/export/', export_views.PatientDataExportView.as_view(), name='export_patient_data'),
    path('export/', export_views.PatientListExportView.as_view(), name='export_patient_list'),
]