# website/urls.py
from django.urls import path
from .views import LandingPageView, PrivacyPolicyView

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing_page'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]