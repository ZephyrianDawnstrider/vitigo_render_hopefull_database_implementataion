from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import SimpleQuerySerializer

class SimpleQueryCreateAPI(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SimpleQuerySerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Query created successfully',
                'query_id': query.query_id,
                'user_email': query.user.email,
                'is_new_user': not bool(query.user.date_joined)  # Check if user was just created
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

def create_test_user():
    """Helper function to create a test user"""
    User = get_user_model()
    email = 'testuser@example.com'
    password = 'testpass123'
    
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    
    if created:
        user.set_password(password)
        user.save()
    
    return {
        'email': email,
        'password': password
    }