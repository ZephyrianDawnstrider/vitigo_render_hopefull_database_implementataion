from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationManagementView.as_view(), name='notification_management'),
]