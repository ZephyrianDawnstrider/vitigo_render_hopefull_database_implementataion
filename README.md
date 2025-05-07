# 🏥 VitiGo Patient Management System

![VitiGo PMS Logo](https://via.placeholder.com/150x150.png?text=VitiGo+PMS)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-3.2-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📚 Table of Contents

- [About](#-about)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

## 🌟 About

VitiGo Patient Management System is a comprehensive software solution designed to streamline and enhance the operations of vitiligo treatment centers. This system comprises a desktop application for doctors, staff, and administrators, as well as a mobile application for patients.

## 🚀 Features

- 👥 **Multi-user Role-based Access Control**
- 📅 **Appointment Scheduling and Management**
- 👨‍⚕️ **Patient Records and Medical History**
- 💊 **Prescription Management**
- 📊 **Treatment Planning and Tracking**
- 📷 **Image Management for Patient Progress**
- 🧪 **Lab Results Integration**
- 💰 **Billing and Financial Management**
- 📊 **Reporting and Analytics**
- 📱 **Patient Mobile App**
- 🖥️ **Telemedicine Support**

## 🏗 System Architecture

The VitiGo PMS is built on a modular, scalable architecture:

- **Backend**: Python with Django framework
- **Frontend (Desktop)**: React.js
- **Mobile App**: React Native (Android, iOS planned)
- **Database**: PostgreSQL
- **API**: Django REST Framework
- **Authentication**: JWT (JSON Web Tokens)
- **Cloud Services**: AWS (Amazon Web Services)
- **Task Queue**: Celery with Redis
- **Search**: Elasticsearch
- **Containerization**: Docker

## 💻 Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/vitigo-pms.git
   cd vitigo-pms
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up the database (PostgreSQL or MySQL):

   ### PostgreSQL Setup
   Create a PostgreSQL database and update the `DATABASES` configuration in `vitigo_pms/settings.py`.

   ### MySQL Setup
   1. Install MySQL server and client libraries
   2. Install python mysqlclient: `pip install mysqlclient`
   3. Create database and user:
   ```sql
   CREATE DATABASE vitigo_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'vitigo_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON vitigo_db.* TO 'vitigo_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
   4. Set environment variables:
   ```bash
   export DB_NAME=vitigo_db
   export DB_USER=vitigo_user
   export DB_PASSWORD=your_password
   export DB_HOST=localhost
   export DB_PORT=3306
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```
   python manage.py runserver
   ```

Visit `http://localhost:8000/admin/` and log in with your superuser credentials.

## 🖱 Usage

Detailed usage instructions for different user roles:

- **Administrators**: Full access to all modules for system management and configuration.
- **Doctors**: Access to patient records, consultation management, and treatment planning.
- **Nurses**: Assist in patient care, manage phototherapy sessions, and update basic health information.
- **Receptionists**: Handle appointments, queries, and patient registration.
- **Pharmacists**: Manage medication inventory and prescription fulfillment.
- **Lab Technicians**: Manage lab tests and reports.
- **Patients (Mobile App)**: View treatment plans, schedule appointments, and upload progress photos.

## 📘 API Documentation

API documentation is available at `/api/docs/` when running the development server.

## 🤝 Contributing

We welcome contributions to the VitiGo Patient Management System! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

Priyanshu Sharma - [ps4798214@gmail.com](mailto:ps4798214@gmail.com)

Project Link: [https://github.com/phostilite/vitigo-pms](https://github.com/phostilite/vitigo-pms)



"# vitigo_render_hopefull_database_implementataion" 
