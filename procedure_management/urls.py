from django.urls import path
from .views import (
    dashboard as dashboard_views,
    procedures as procedure_views,
    consents as consent_views,
    categories as category_views,
    types as types_views,
    prerequisites as prerequisites_views,
    instructions as instructions_views,
    media as media_views,
    checklists as checklist_views,
    checklist_templates as template_views,
)

app_name = 'procedure_management'

urlpatterns = [
    # Dashboard URL
    path('', dashboard_views.ProcedureManagementView.as_view(), name='procedure_management'),
    
    # Procedure URLs
    path('procedures/', procedure_views.ProcedureListView.as_view(), name='procedure_list'),
    path('procedures/create/', procedure_views.ProcedureCreateView.as_view(), name='procedure_create'),
    path('procedures/<int:pk>/', procedure_views.ProcedureDetailView.as_view(), name='procedure_detail'),
    path('procedures/<int:pk>/edit/', procedure_views.ProcedureUpdateView.as_view(), name='procedure_update'),
    path('procedures/<int:pk>/delete/', procedure_views.ProcedureDeleteView.as_view(), name='procedure_delete'),
    
    # Consent Form URLs
    path('consents/', consent_views.ConsentFormListView.as_view(), name='consent_list'),
    path('consents/create/', consent_views.ConsentFormCreateView.as_view(), name='consent_create'),
    path('consents/<int:pk>/', consent_views.ConsentFormDetailView.as_view(), name='consent_detail'),
    path('consents/<int:pk>/edit/', consent_views.ConsentFormUpdateView.as_view(), name='consent_update'),
    path('consents/<int:pk>/delete/', consent_views.ConsentFormDeleteView.as_view(), name='consent_delete'),
    
    # Category URLs
    path('categories/', category_views.ProcedureCategoryListView.as_view(), name='category_list'),
    path('categories/create/', category_views.ProcedureCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/', category_views.ProcedureCategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', category_views.ProcedureCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', category_views.ProcedureCategoryDeleteView.as_view(), name='category_delete'),
    
    # Procedure Type URLs
    path('types/', types_views.ProcedureTypeListView.as_view(), name='type_list'),
    path('types/create/', types_views.ProcedureTypeCreateView.as_view(), name='type_create'),
    path('types/<int:pk>/', types_views.ProcedureTypeDetailView.as_view(), name='type_detail'),
    path('types/<int:pk>/edit/', types_views.ProcedureTypeUpdateView.as_view(), name='type_update'),
    path('types/<int:pk>/delete/', types_views.ProcedureTypeDeleteView.as_view(), name='type_delete'),
    
    # Prerequisites URLs
    path('prerequisites/', prerequisites_views.PrerequisiteListView.as_view(), name='prerequisite_list'),
    path('prerequisites/create/', prerequisites_views.PrerequisiteCreateView.as_view(), name='prerequisite_create'),
    path('prerequisites/<int:pk>/', prerequisites_views.PrerequisiteDetailView.as_view(), name='prerequisite_detail'),
    path('prerequisites/<int:pk>/edit/', prerequisites_views.PrerequisiteUpdateView.as_view(), name='prerequisite_update'),
    path('prerequisites/<int:pk>/delete/', prerequisites_views.PrerequisiteDeleteView.as_view(), name='prerequisite_delete'),
    
    # Instructions URLs
    path('instructions/', instructions_views.InstructionListView.as_view(), name='instruction_list'),
    path('instructions/create/', instructions_views.InstructionCreateView.as_view(), name='instruction_create'),
    path('instructions/<int:pk>/', instructions_views.InstructionDetailView.as_view(), name='instruction_detail'),
    path('instructions/<int:pk>/edit/', instructions_views.InstructionUpdateView.as_view(), name='instruction_update'),
    path('instructions/<int:pk>/delete/', instructions_views.InstructionDeleteView.as_view(), name='instruction_delete'),
    
    # Media URLs
    path('media/', media_views.MediaListView.as_view(), name='media_list'),
    path('media/create/', media_views.MediaCreateView.as_view(), name='media_create'),
    path('media/<int:pk>/', media_views.MediaDetailView.as_view(), name='media_detail'),
    path('media/<int:pk>/edit/', media_views.MediaUpdateView.as_view(), name='media_update'),
    path('media/<int:pk>/delete/', media_views.MediaDeleteView.as_view(), name='media_delete'),
    
    # Checklist URLs
    path('checklists/', checklist_views.ChecklistListView.as_view(), name='checklist_list'),
    path('checklists/create/', checklist_views.ChecklistCreateView.as_view(), name='checklist_create'),
    path('checklists/<int:pk>/', checklist_views.ChecklistDetailView.as_view(), name='checklist_detail'),
    path('checklists/<int:pk>/edit/', checklist_views.ChecklistUpdateView.as_view(), name='checklist_update'),
    path('checklists/<int:pk>/delete/', checklist_views.ChecklistDeleteView.as_view(), name='checklist_delete'),
    
    # Checklist Template URLs
    path('templates/', template_views.ChecklistTemplateListView.as_view(), name='template_list'),
    path('templates/create/', template_views.ChecklistTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', template_views.ChecklistTemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/edit/', template_views.ChecklistTemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/delete/', template_views.ChecklistTemplateDeleteView.as_view(), name='template_delete'),
]