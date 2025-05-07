from django.urls import path
from . import views

urlpatterns = [
    path('', views.FinanceManagementView.as_view(), name='finance_management'),
]