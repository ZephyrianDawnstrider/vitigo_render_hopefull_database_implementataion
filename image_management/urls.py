from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageManagementView.as_view(), name='image_management'),
    path('upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('upload/confirmation/', views.ImageUploadConfirmationView.as_view(), name='image_upload_confirmation'),
    path('image/<int:image_id>/download/', views.DownloadImageView.as_view(), name='download_image'),
    path('image/<int:image_id>/delete/', views.DeleteImageView.as_view(), name='delete_image'),
    path('image/<int:image_id>/details/', views.ImageDetailView.as_view(), name='image_detail'),
    path('export/', views.ImageExportView.as_view(), name='export_images'),

    path('comparisons/', views.ImageComparisonListView.as_view(), name='comparison_list'),
    path('comparison/create/', views.ImageComparisonCreateView.as_view(), name='comparison_create'),
    path('comparison/<int:pk>/', views.ImageComparisonDetailView.as_view(), name='comparison_detail'),

    path('human-3d/', views.Human3DModelView.as_view(), name='human_3d'),
]