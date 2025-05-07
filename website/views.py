# website/views.py
import logging
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

class LandingPageView(View):
    def get(self, request):
        try:
            return render(request, 'website/landing_page.html')
        except Exception as e:
            logger.error(f"Error rendering landing page: {str(e)}")
            return render(request, 'error_handling/500.html', status=500)
        
class PrivacyPolicyView(View):
    def get(self, request):
        try:
            return render(request, 'website/privacy_policy.html')
        except Exception as e:
            logger.error(f"Error rendering privacy policy page: {str(e)}")
            return render(request, 'error_handling/500.html', status=500)