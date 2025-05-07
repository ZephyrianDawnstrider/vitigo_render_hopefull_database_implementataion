import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from django.shortcuts import render
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    UserLoginSerializer,
    BasicUserInfoUpdateSerializer,
    PasswordResetRequestSerializer,
    SubscriptionSerializer,
    RoleSerializer  # Add RoleSerializer to imports
)
from user_management.serializers import CustomUserSerializer
from api.custom_auth import CustomTokenAuthentication
from access_control.models import Role
from patient_management.models import Patient
from patient_management.serializers import PatientSerializer
from subscription_management.models import Subscription, SubscriptionTier

User = get_user_model()
logger = logging.getLogger(__name__)

class UserRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            
            # Check required fields
            required_fields = ['email', 'password', 'first_name', 'last_name']
            for field in required_fields:
                if not data.get(field):
                    return Response({
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if email exists
            if User.objects.filter(email=data['email']).exists():
                return Response({
                    'error': 'Email already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user without role
            user = User(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_number=data.get('phone_number', '')
            )
            user.set_password(data['password'])
            # The role will be assigned by the signal
            user.save()
            
            token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'User registered successfully',
                'data': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'token': token.key
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'error': 'Registration failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoleListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            roles = Role.objects.all()
            role_data = [{'id': role.id, 'name': role.name} for role in roles]
            return Response({
                'status': 'success',
                'data': role_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching roles: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch roles'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserRoleAssignmentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        role_id = request.data.get('role_id')

        if not user_id or not role_id:
            return Response({
                'status': 'error',
                'message': 'Both user_id and role_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)

            user.role = role
            user.save()

            return Response({
                'status': 'success',
                'message': f'Role {role.name} assigned to user successfully',
                'data': {
                    'user_id': user.id,
                    'role': role.name
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Role not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to assign role'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UserLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            
            # Get role data using RoleSerializer if role exists
            role_data = RoleSerializer(user.role).data if user.role else None
            
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'data': {
                    'token': token.key,
                    'user_id': user.pk,
                    'email': user.email,
                    'role': role_data
                }
            }, status=status.HTTP_200_OK)
        return Response({
            'status': 'error',
            'message': 'Login failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



class UserInfoView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_data = CustomUserSerializer(user).data
        response_data = {'user': user_data}

        # Attempt to get patient data
        try:
            patient = Patient.objects.get(user=user)
            response_data['patient'] = PatientSerializer(patient).data
        except Patient.DoesNotExist:
            response_data['patient'] = None

        # Attempt to get subscription data
        try:
            subscription = Subscription.objects.get(user=user)
            response_data['subscription'] = SubscriptionSerializer(subscription).data
        except Subscription.DoesNotExist:
            response_data['subscription'] = None

        # Add role-specific message
        if user.role == 'PATIENT':
            if response_data['patient'] is None:
                response_data['message'] = "Patient profile not found. Please complete your profile."
            elif response_data['subscription'] is None:
                response_data['message'] = "No active subscription found. Please subscribe to access full features."
        else:
            response_data['message'] = f"User role is {user.role}. Additional role-specific data will be implemented in the future."

        return Response(response_data, status=status.HTTP_200_OK)


class BasicUserInfoUpdateAPIView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = BasicUserInfoUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
        try:
            if serializer.is_valid():
                if 'password' in serializer.validated_data:
                    user.set_password(serializer.validated_data['password'])
                    serializer.validated_data.pop('password')

                serializer.save()
                logger.info(f"User {user.id} information updated successfully")
                return Response({
                    'status': 'success',
                    'message': 'User information updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"User {user.id} update failed: {serializer.errors}")
                return Response({
                    'status': 'error',
                    'message': 'Update failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating user {user.id} information: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        logger.info("Password reset request received")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            logger.info(f"Processing password reset request for email: {email}")
            try:
                user = User.objects.filter(email=email).first()
                if user:
                    logger.info(f"User found for email: {email}")
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))

                    # Check if FRONTEND_URL is set
                    if not hasattr(settings, 'FRONTEND_URL') or not settings.FRONTEND_URL:
                        logger.error("FRONTEND_URL is not set in settings")
                        return Response({
                            "error": "Server configuration error. Please contact the administrator."
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    reset_link = f"{settings.FRONTEND_URL}/api/reset-password/{uid}/{token}/"
                    logger.info(f"Reset link generated: {reset_link}")

                    # Send email
                    subject = "Password Reset Request"
                    message = f"Please use this link to reset your password: {reset_link}"
                    try:
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                        logger.info(f"Password reset email sent to: {email}")
                    except Exception as e:
                        logger.error(f"Failed to send password reset email: {str(e)}", exc_info=True)
                        return Response({
                            "error": "Failed to send password reset email. Please try again later."
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    logger.info(f"No user found for email: {email}")

                return Response({
                    "message": "If an account exists with this email, a password reset link has been sent."
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error processing password reset request: {str(e)}", exc_info=True)
                return Response({
                    "error": "An unexpected error occurred. Please try again later."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.warning(f"Invalid password reset request data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    template_name = 'password_reset/password_reset_confirm.html'

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            context = {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
            }
        else:
            context = {'valid': False}

        return render(request, self.template_name, context)

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "New password is required"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Invalid reset link"}, status=status.HTTP_400_BAD_REQUEST)