from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()

class EmailOrPhoneAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        
        try:
            # Check if username is an email
            if '@' in str(username):
                user = UserModel.objects.get(email=username)
            # If not email, try phone authentication
            elif 'country_code' in kwargs and 'phone_number' in kwargs:
                user = UserModel.objects.get(
                    country_code=kwargs['country_code'],
                    phone_number=kwargs['phone_number']
                )
            else:
                return None
                
            if user.check_password(password):
                return user
                
        except UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None