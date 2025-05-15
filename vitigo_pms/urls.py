"""
URL configuration for vitigo_pms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="VitiGo API",
        default_version='v1',
        description="API documentation for VitiGo Patient Management System",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('asset/', include('asset_management.urls')),
    path('access-control/', include('access_control.urls')),
    path('webhooks/', include('webhooks.urls')),
    path('', include('website.urls')),
    path('accounts/', include('user_management.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('api/', include('api.urls')),
    path('patients/', include('patient_management.urls')),
    path('appointments/', include('appointment_management.urls')),
    path('consultations/', include('consultation_management.urls')),
    path('clinic/', include('clinic_management.urls')),
    path('compliance/', include('compliance_management.urls')),
    path('queries/', include('query_management.urls')),
    path('procedures/', include('procedure_management.urls')),
    path('phototherapy/', include('phototherapy_management.urls')),
    path('pharmacy/', include('pharmacy_management.urls')),
    path('lab/', include('lab_management.urls')),
    path('image/', include('image_management.urls')),
    path('stock/', include('stock_management.urls')),
    path('finance/', include('financial_management.urls')),
    path('hr/', include('hr_management.urls')),
    path('telemedicine/', include('telemedicine_management.urls')),
    path('research/', include('research_management.urls')),
    path('reporting-and-analytics/', include('reporting_and_analytics.urls')),
    path('notifications/', include('notifications.urls')),
    path('help-support/', include('help_support.urls')),
    path('settings/', include(('settings.urls', 'settings'), namespace='settings')),
    path('sandbox/', include('sandbox.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'error_handling.views.handler400'
handler403 = 'error_handling.views.handler403'
handler404 = 'error_handling.views.handler404'
handler500 = 'error_handling.views.handler500'
handler401 = 'error_handling.views.handler401'
handler405 = 'error_handling.views.handler405'
handler422 = 'error_handling.views.handler422'
handler429 = 'error_handling.views.handler429'