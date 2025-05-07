from django.contrib import admin
# Fix the imports to use relative imports from the app
from .models.base import Gender, BodyModel, BodyView
from .models.regions import BodyRegion 
from .models.coordinates import BodyImage, CoordinateGroup, Coordinate, RegionMeasurement

# Register the models
admin.site.register(Gender)
admin.site.register(BodyModel)
admin.site.register(BodyView)
admin.site.register(BodyRegion)
admin.site.register(BodyImage)
admin.site.register(CoordinateGroup)
admin.site.register(Coordinate)
admin.site.register(RegionMeasurement)