from django.urls import path
from . import views

urlpatterns = [
    path('', views.TelemedicineManagementView.as_view(), name='telemedicine_management'),
]