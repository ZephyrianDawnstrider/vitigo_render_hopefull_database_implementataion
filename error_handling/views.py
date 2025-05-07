# Standard library imports
import json
import traceback

# Django imports
from django.http import HttpRequest
from django.shortcuts import render

# Local imports
from .models import ErrorLog

def log_error(request: HttpRequest, status_code: int, exception: Exception = None):
    """Helper function to log errors to database"""
    error_level = 'ERROR' if status_code >= 500 else 'WARNING'
    
    error_data = {
        'headers': dict(request.headers),
        'method': request.method,
        'path': request.path,
    }
    
    if hasattr(request, 'user'):
        user = request.user if request.user.is_authenticated else None
    else:
        user = None

    ErrorLog.objects.create(
        level=error_level,
        message=str(exception) if exception else f"HTTP {status_code}",
        traceback=traceback.format_exc() if exception else None,
        user=user,
        url=request.build_absolute_uri(),
        method=request.method,
        data=error_data
    )

def handler400(request: HttpRequest, exception=None):
    log_error(request, 400, exception)
    context = {
        'title': 'Bad Request',
        'error_code': 400,
        'message': str(exception) if exception else 'The request could not be understood by the server',
        'description': 'The request contains invalid syntax or cannot be fulfilled.',
        'path': request.path
    }
    return render(request, 'error_handling/400.html', context, status=400)

def handler401(request: HttpRequest, exception=None):
    log_error(request, 401, exception)
    context = {
        'title': 'Unauthorized',
        'error_code': 401,
        'message': str(exception) if exception else 'Authentication is required',
        'description': 'The requested resource requires authentication.',
        'path': request.path
    }
    return render(request, 'error_handling/401.html', context, status=401)

def handler403(request: HttpRequest, exception=None):
    log_error(request, 403, exception)
    context = {
        'title': 'Forbidden',
        'error_code': 403,
        'message': str(exception) if exception else 'Access to this resource is forbidden',
        'description': 'You do not have permission to access this resource.',
        'path': request.path
    }
    return render(request, 'error_handling/403.html', context, status=403)

def handler404(request: HttpRequest, exception=None):
    log_error(request, 404, exception)
    context = {
        'title': 'Page Not Found',
        'error_code': 404,
        'message': str(exception) if exception else 'The requested page was not found',
        'description': 'The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.',
        'path': request.path
    }
    return render(request, 'error_handling/404.html', context, status=404)

def handler405(request: HttpRequest, exception=None):
    log_error(request, 405, exception)
    context = {
        'title': 'Method Not Allowed',
        'error_code': 405,
        'message': str(exception) if exception else f'Method {request.method} not allowed',
        'description': 'The method specified in the request is not allowed for the resource identified by the request URI.',
        'path': request.path,
        'allowed_methods': request.headers.get('Allow', '')
    }
    return render(request, 'error_handling/405.html', context, status=405)

def handler422(request: HttpRequest, exception=None):
    log_error(request, 422, exception)
    context = {
        'title': 'Unprocessable Entity',
        'error_code': 422,
        'message': str(exception) if exception else 'The request was well-formed but could not be processed',
        'description': 'The server understands the content type and syntax of the request but was unable to process the contained instructions.',
        'path': request.path
    }
    return render(request, 'error_handling/422.html', context, status=422)

def handler429(request: HttpRequest, exception=None):
    log_error(request, 429, exception)
    context = {
        'title': 'Too Many Requests',
        'error_code': 429,
        'message': str(exception) if exception else 'Rate limit exceeded',
        'description': 'You have sent too many requests in a given amount of time.',
        'path': request.path
    }
    return render(request, 'error_handling/429.html', context, status=429)

def handler500(request: HttpRequest, exception=None):
    log_error(request, 500, exception)
    context = {
        'title': 'Internal Server Error',
        'error_code': 500,
        'message': str(exception) if exception else 'An unexpected error occurred',
        'description': 'The server encountered an internal error and was unable to complete your request.',
        'path': request.path,
        'request_id': request.headers.get('X-Request-ID', ''),
        'debug': request.META.get('DEBUG', False)
    }
    return render(request, 'error_handling/500.html', context, status=500)