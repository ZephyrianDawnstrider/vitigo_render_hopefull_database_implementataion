from django.urls import path
from . import views

urlpatterns = [
    path('', views.LabManagementView.as_view(), name='lab_management'),
]