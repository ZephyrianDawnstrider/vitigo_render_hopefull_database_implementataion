# user_management/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'error': {
                'status_code': response.status_code,
                'detail': response.data
            }
        }
        response.data = custom_response_data
    else:
        custom_response_data = {
            'error': {
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'detail': 'A server error occurred.'
            }
        }
        response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response