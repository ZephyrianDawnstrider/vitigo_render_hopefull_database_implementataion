#!/bin/bash

# Function to handle errors
handle_error() {
    echo "ERROR: $1"
    exit 1
}

echo "Starting Django project cleanup..."

# Delete migrations and cache files
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete || handle_error "Failed to delete migration files"
find . -name "__pycache__" -type d -exec rm -r {} + || handle_error "Failed to delete __pycache__ directories"
find . -name "db.sqlite3" -delete || handle_error "Failed to delete database file"

# Deactivate and remove virtual environment
deactivate 2>/dev/null
rm -rf env || handle_error "Failed to remove existing virtual environment"

# Create new virtual environment
python3 -m venv env || handle_error "Failed to create virtual environment"
source env/bin/activate || handle_error "Failed to activate virtual environment"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    handle_error "Virtual environment activation failed"
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || handle_error "Failed to install requirements"
else
    handle_error "requirements.txt not found"
fi

# Django commands with enhanced error handling
python manage.py makemigrations || handle_error "Failed to make migrations"
python manage.py migrate || handle_error "Failed to apply migrations"

# Create superuser non-interactively
echo "Creating superuser..."
python manage.py shell << EOF || handle_error "Failed to create superuser"
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(email='admin@test.com').exists():
        User.objects.create_superuser('admin@test.com', 'Test@123')
        print('Superuser created successfully')
    else:
        print('Superuser already exists')
except Exception as e:
    print(f'Failed to create superuser: {str(e)}')
    exit(1)
EOF

# Run custom management commands with error handling
echo "Running custom management commands..."
python manage.py collectstatic --noinput || handle_error "Failed to collect static files"

echo "✅ Cleanup completed successfully!"