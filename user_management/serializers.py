from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'role', 'profile_picture']
        read_only_fields = ['id', 'date_joined', 'is_active']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['full_name'] = instance.get_full_name()
        if instance.profile_picture:
            request = self.context.get('request')
            if request is not None:
                representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url)
            else:
                representation['profile_picture'] = f"{settings.BASE_URL}{instance.profile_picture.url}"
        else:
            representation['profile_picture'] = None
        return representation

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email address.")
        return value