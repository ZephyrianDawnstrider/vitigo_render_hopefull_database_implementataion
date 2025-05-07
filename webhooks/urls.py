# urls.py
from django.urls import path
from webhooks import views

urlpatterns = [
    path('whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('messenger/', views.messenger_webhook, name='messenger_webhook'),
    path('instagram/', views.instagram_webhook, name='instagram_webhook'),
    path('chatbot/', views.chatbot_webhook, name='chatbot_webhook'),
]