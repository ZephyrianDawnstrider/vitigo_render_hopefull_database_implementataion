from django.urls import path
from . import views

urlpatterns = [
    path('', views.HelpSupportManagementView.as_view(), name='help_support_management'),
]