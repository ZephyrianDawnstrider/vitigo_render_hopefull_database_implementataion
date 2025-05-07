from django.urls import path
from . import views

urlpatterns = [
    path('', views.StockManagementView.as_view(), name='stock_management'),
]