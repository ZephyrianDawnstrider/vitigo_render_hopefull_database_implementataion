# views.py
from django.shortcuts import render
from body_mapping.models.base import Gender, BodyModel, BodyView
from body_mapping.models.regions import BodyRegion
from body_mapping.models.coordinates import (
    BodyImage, CoordinateGroup, Coordinate, RegionMeasurement
)

def image_carousel(request):
    selected_gender = request.GET.get('gender', 'M')
    
    # Get the body model for selected gender
    body_model = BodyModel.objects.filter(
        gender__code=selected_gender,
        is_active=True
    ).first()
    
    if body_model:
        # Get all images with their related data
        images = BodyImage.objects.filter(
            body_model=body_model
        ).select_related('view').order_by('view__display_order')
        
        # Prepare image data with their regions and coordinates
        image_data = []
        for img in images:
            # Get all coordinate groups (regions) for this image
            coordinate_groups = CoordinateGroup.objects.filter(
                body_image=img
            ).select_related('body_region').prefetch_related('coordinates')
            
            # Prepare regions data
            regions_data = {}
            for group in coordinate_groups:
                # Get coordinates in sequence order
                coordinates = list(group.coordinates.order_by('sequence').values(
                    'label',
                    'x_coordinate',
                    'y_coordinate',
                    'sequence'
                ))
                
                # Get measurements if they exist
                measurements = RegionMeasurement.objects.filter(
                    coordinate_group=group
                ).values('name', 'value', 'unit', 'measurement_type')
                
                regions_data[group.body_region.code] = {
                    'name': group.body_region.name,
                    'description': group.body_region.description,
                    'coordinates': coordinates,
                    'measurements': list(measurements)
                }
            
            image_data.append({
                'id': img.id,
                'src': img.image.url,
                'alt': f'{img.body_model.gender.name} - {img.view.name}',
                'view_code': img.view.code,
                'regions': regions_data
            })
    else:
        image_data = []
    
    context = {
        'images': image_data,
        'selected_gender': selected_gender,
    }
    
    return render(request, 'sandbox/image_coordinates.html', context)