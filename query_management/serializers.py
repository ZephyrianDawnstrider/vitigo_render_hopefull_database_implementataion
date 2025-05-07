from rest_framework import serializers
from .models import Query, QueryTag, QueryAttachment
from django.contrib.auth import get_user_model

class ChoiceSerializer(serializers.Serializer):
    value = serializers.CharField()
    display = serializers.CharField()

class QueryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryTag
        fields = ['id', 'name']

class QueryAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryAttachment
        fields = ['id', 'file', 'uploaded_at']

class QuerySerializer(serializers.ModelSerializer):
    tags = QueryTagSerializer(many=True, read_only=True)
    attachments = QueryAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Query
        fields = '__all__'
        extra_kwargs = {
            'status': {'required': False},
            'priority': {'required': False},
            'tags': {'required': False},
            'contact_email': {'required': False},
            'contact_phone': {'required': False},
            'attachments': {'required': False}
        }

class SimpleQuerySerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    description = serializers.CharField(required=True)

    class Meta:
        model = Query
        fields = ['first_name', 'last_name', 'email', 'description']

    def create(self, validated_data):
        # Extract user data
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        description = validated_data.pop('description')

        # Get or create user
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True
            }
        )

        # Create query with user
        query = Query.objects.create(
            user=user,
            subject=f"Query from {first_name} {last_name}",
            description=description,  # Now using the provided description
            source='WEBSITE',
            priority='B',
            status='NEW',
            contact_email=email,
            is_anonymous=False
        )
        return query