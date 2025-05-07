# Use official Python image as base
FROM python:3.11-slim

# Install system dependencies for ODBC Driver 17 and other requirements
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && apt-get remove -y libodbc2 libodbcinst2 unixodbc-common \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies

# Install build dependencies for mysqlclient
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

# Expose port (match Render port environment variable)
EXPOSE 10000

# Set environment variable for Django settings module if needed
ENV DJANGO_SETTINGS_MODULE=vitigo_pms.production_settings

# Start Gunicorn server
CMD ["gunicorn", "vitigo_pms.wsgi:application", "--bind", "0.0.0.0:10000", "--workers", "3", "--timeout", "120"]
