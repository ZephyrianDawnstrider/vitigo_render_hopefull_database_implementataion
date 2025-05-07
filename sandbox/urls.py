# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('image-carousel/', views.image_carousel, name='image_carousel'),
]