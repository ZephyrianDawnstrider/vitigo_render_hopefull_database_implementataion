from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResearchManagementView.as_view(), name='research_management'),
]