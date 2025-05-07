# body_mapping/management/commands/populate_body_mapping.py
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from body_mapping.models.base import Gender, BodyView
from body_mapping.models.regions import BodyRegion
from body_mapping.models.coordinates import BodyModel, BodyImage, CoordinateGroup, Coordinate, RegionMeasurement
from pathlib import Path

class Command(BaseCommand):
    help = 'Populate body mapping models with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')
        
        # Create Genders
        genders_data = [
            {'name': 'Male', 'code': 'M', 'description': 'Male body type'},
            {'name': 'Female', 'code': 'F', 'description': 'Female body type'},
        ]
        genders = {}
        for data in genders_data:
            gender, created = Gender.objects.get_or_create(**data)
            genders[data['code']] = gender
            self.stdout.write(f'Created gender: {gender.name}')

        # Create Body Views
        views_data = [
            {'name': 'Front View', 'code': 'FRONT', 'display_order': 1, 'description': 'Front view of body'},
            {'name': 'Back View', 'code': 'BACK', 'display_order': 2, 'description': 'Back view of body'},
            {'name': 'Left Side', 'code': 'LEFT', 'display_order': 3, 'description': 'Left side view'},
            {'name': 'Right Side', 'code': 'RIGHT', 'display_order': 4, 'description': 'Right side view'},
        ]
        views = {}
        for data in views_data:
            view, created = BodyView.objects.get_or_create(**data)
            views[data['code']] = view
            self.stdout.write(f'Created view: {view.name}')

        # Create Body Regions
        regions_data = [
            {
                'name': 'Torso',
                'code': 'TORSO',
                'description': 'Main body trunk',
                'parent_region': None
            },
            {
                'name': 'Chest',
                'code': 'CHEST',
                'description': 'Chest area',
                'parent_region': 'TORSO'
            },
            {
                'name': 'Left Chest',
                'code': 'LEFT_CHEST',
                'description': 'Left chest area',
                'parent_region': 'CHEST'
            },
            {
                'name': 'Right Chest',
                'code': 'RIGHT_CHEST',
                'description': 'Right chest area',
                'parent_region': 'CHEST'
            },
            {
                'name': 'Abdomen',
                'code': 'ABDOMEN',
                'description': 'Abdominal area',
                'parent_region': 'TORSO'
            },
            {
                'name': 'Upper Abdomen',
                'code': 'UPPER_ABDOMEN',
                'description': 'Upper abdominal area',
                'parent_region': 'ABDOMEN'
            },
            {
                'name': 'Lower Abdomen',
                'code': 'LOWER_ABDOMEN',
                'description': 'Lower abdominal area',
                'parent_region': 'ABDOMEN'
            }
        ]

        regions = {}
        for data in regions_data:
            parent_code = data.pop('parent_region')
            if parent_code:
                data['parent_region'] = regions[parent_code]
            region, created = BodyRegion.objects.get_or_create(**data)
            regions[data['code']] = region
            # Add applicable views
            region.applicable_views.add(*views.values())
            self.stdout.write(f'Created region: {region.name}')

        # Create Body Models
        models_data = [
            {
                'name': 'Standard Male Model',
                'description': 'Standard male body model for measurements',
                'gender': genders['M'],
                'version': '1.0'
            },
            {
                'name': 'Standard Female Model',
                'description': 'Standard female body model for measurements',
                'gender': genders['F'],
                'version': '1.0'
            }
        ]
        body_models = {}
        for data in models_data:
            model, created = BodyModel.objects.get_or_create(**data)
            body_models[model.name] = model
            self.stdout.write(f'Created body model: {model.name}')

        # Create Body Images (assuming you have image files)
        # In practice, you'd need actual image files
        images_data = [
            {
                'body_model': 'Standard Male Model',
                'view': 'FRONT',
                'resolution': '1920x1080',
                'image_quality': 90,
                'metadata': {'format': 'JPEG', 'color_space': 'RGB'}
            },
            {
                'body_model': 'Standard Male Model',
                'view': 'BACK',
                'resolution': '1920x1080',
                'image_quality': 90,
                'metadata': {'format': 'JPEG', 'color_space': 'RGB'}
            }
        ]

        for data in images_data:
            # Create a dummy image file for demonstration
            dummy_image = ContentFile(b'dummy_image_content')
            model_name = data.pop('body_model')
            view_code = data.pop('view')
            image = BodyImage.objects.create(
                body_model=body_models[model_name],
                view=views[view_code],
                **data
            )
            image.image.save(f'dummy_{model_name}_{view_code}.jpg', dummy_image)
            self.stdout.write(f'Created body image: {image}')

        # Create Coordinate Groups and Coordinates
        coordinate_groups_data = [
            {
                'body_image': ('Standard Male Model', 'FRONT'),
                'body_region': 'LEFT_CHEST',
                'name': 'Left Chest Measurement Points',
                'description': 'Points defining left chest area',
                'coordinates': [
                    {'label': 'A', 'x_coordinate': 100, 'y_coordinate': 100, 'sequence': 0},
                    {'label': 'B', 'x_coordinate': 200, 'y_coordinate': 100, 'sequence': 1},
                    {'label': 'C', 'x_coordinate': 200, 'y_coordinate': 200, 'sequence': 2},
                    {'label': 'D', 'x_coordinate': 100, 'y_coordinate': 200, 'sequence': 3},
                ]
            }
        ]

        for group_data in coordinate_groups_data:
            model_name, view_code = group_data.pop('body_image')
            region_code = group_data.pop('body_region')
            coordinates = group_data.pop('coordinates')
            
            body_image = BodyImage.objects.get(
                body_model=body_models[model_name],
                view=views[view_code]
            )
            
            coordinate_group = CoordinateGroup.objects.create(
                body_image=body_image,
                body_region=regions[region_code],
                **group_data
            )

            for coord_data in coordinates:
                Coordinate.objects.create(
                    coordinate_group=coordinate_group,
                    **coord_data
                )
            
            self.stdout.write(f'Created coordinate group: {coordinate_group}')

            # Create measurements for the coordinate group
            measurements_data = [
                {
                    'name': 'Area',
                    'value': 10000,
                    'unit': 'px²',
                    'measurement_type': 'area'
                },
                {
                    'name': 'Perimeter',
                    'value': 400,
                    'unit': 'px',
                    'measurement_type': 'distance'
                }
            ]

            for measurement_data in measurements_data:
                RegionMeasurement.objects.create(
                    coordinate_group=coordinate_group,
                    **measurement_data
                )
                self.stdout.write(f'Created measurement for {coordinate_group}')

        self.stdout.write(self.style.SUCCESS('Successfully populated body mapping data'))