import logging
from datetime import datetime, timedelta

# Django and DRF imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import DatabaseError
from django.db.utils import IntegrityError 
from django.shortcuts import render, get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

# Swagger imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Custom authentication
from .custom_auth import CustomTokenAuthentication

# Serializers
from .serializers import (
    PatientSerializer
)
from patient_management.serializers import (
    MedicalHistorySerializer, MedicationSerializer, VitiligoAssessmentSerializer, TreatmentPlanSerializer, PatientCreateSerializer, MedicalHistoryCreateSerializer, MedicalHistoryUpdateSerializer, PatientUpdateSerializer
)
from appointment_management.serializers import (
    AppointmentSerializer, AppointmentCreateSerializer, DoctorTimeSlotSerializer, DoctorTimeSlotDetailSerializer
)
from query_management.serializers import QuerySerializer
from doctor_management.serializers import (
    DoctorListSerializer, DoctorDetailSerializer, SpecializationSerializer, TreatmentMethodSerializer,
    BodyAreaSerializer, AssociatedConditionSerializer
)
from query_management.serializers import QuerySerializer, QueryTagSerializer, ChoiceSerializer

# Models
from patient_management.models import (
    Patient, MedicalHistory, Medication, VitiligoAssessment, TreatmentPlan
)
from appointment_management.models import Appointment, DoctorTimeSlot
from query_management.models import Query, QueryTag, QueryAttachment
from doctor_management.models import (
    DoctorProfile, Specialization, TreatmentMethodSpecialization, BodyAreaSpecialization, AssociatedConditionSpecialization
)

User = get_user_model()
logger = logging.getLogger(__name__)

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                             PATIENT VIEWS                                    ║
║ Handles all patient-specific operations including profile management,        ║
║ medical history, and patient-specific data retrieval.                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class PatientInfoView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role.name != 'PATIENT':
            return Response({"error": "Only patients can access this information"}, status=status.HTTP_403_FORBIDDEN)

        try:
            patient = Patient.objects.get(user=user)
            response_data = self.get_patient_data(patient)
            return Response(response_data, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            logger.warning(f"Patient profile not found for user {user.id}")
            return Response({"error": "Patient profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving patient information for user {user.id}: {str(e)}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_patient_data(self, patient):
        data = {
            "patient": PatientSerializer(patient).data,
            "medical_history": self.get_medical_history(patient),
            "medications": self.get_medications(patient),
            "vitiligo_assessments": self.get_vitiligo_assessments(patient),
            "treatment_plans": self.get_treatment_plans(patient)
        }
        return data

    def get_medical_history(self, patient):
        try:
            medical_history = MedicalHistory.objects.get(patient=patient)
            return MedicalHistorySerializer(medical_history).data
        except MedicalHistory.DoesNotExist:
            return None

    def get_medications(self, patient):
        medications = Medication.objects.filter(patient=patient)
        return MedicationSerializer(medications, many=True).data

    def get_vitiligo_assessments(self, patient):
        assessments = VitiligoAssessment.objects.filter(patient=patient).order_by('-assessment_date')
        return VitiligoAssessmentSerializer(assessments, many=True).data

    def get_treatment_plans(self, patient):
        plans = TreatmentPlan.objects.filter(patient=patient).order_by('-created_date')
        return TreatmentPlanSerializer(plans, many=True).data
    

class PatientProfileAPIView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            serializer = PatientCreateSerializer(
                data=request.data, 
                context={'user': user, 'request': request, 'user_id': user_id}  # Include user_id in context
            )
            if serializer.is_valid():
                patient = serializer.save(user=user)
                logger.info(f"Patient profile created successfully for user {user_id}")
                return Response({
                    'status': 'success',
                    'message': 'Patient profile created successfully',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"Patient profile creation failed: {serializer.errors}")
                return Response({
                    'status': 'error',
                    'message': 'Creation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating patient profile: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            serializer = PatientUpdateSerializer(patient)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            raise NotFound('User not found')
        except Patient.DoesNotExist:
            logger.error(f"Patient profile for user {user_id} not found")
            raise NotFound('Patient profile not found')
        except Exception as e:
            logger.error(f"Error retrieving patient profile: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve patient profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            serializer = PatientUpdateSerializer(patient, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Patient profile updated successfully for user {user_id}")
                return Response({
                    'status': 'success',
                    'message': 'Patient profile updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Patient profile update failed: {serializer.errors}")
                return Response({
                    'status': 'error',
                    'message': 'Update failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            raise NotFound('User not found')
        except Patient.DoesNotExist:
            logger.error(f"Patient profile for user {user_id} not found")
            raise NotFound('Patient profile not found')
        except Exception as e:
            logger.error(f"Error updating patient profile: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicalHistoryAPIView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            
            # Check if medical history already exists
            existing_history = MedicalHistory.objects.filter(patient=patient).exists()
            if existing_history:
                logger.warning(f"Medical history already exists for user {user_id}")
                return Response({
                    'status': 'error',
                    'message': 'Medical history already exists for this patient',
                    'code': 'duplicate_record'
                }, status=status.HTTP_409_CONFLICT)
                
            serializer = MedicalHistoryCreateSerializer(
                data=request.data, 
                context={'patient': patient, 'request': request}
            )
            if serializer.is_valid():
                medical_history = serializer.save(patient=patient)
                logger.info(f"Medical history created successfully for user {user_id}")
                return Response({
                    'status': 'success',
                    'message': 'Medical history created successfully',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"Medical history creation failed: {serializer.errors}")
                return Response({
                    'status': 'error',
                    'message': 'Creation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            logger.error(f"Integrity error while creating medical history: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Medical history already exists for this patient',
                'code': 'duplicate_record'
            }, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Error creating medical history: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            medical_history = get_object_or_404(MedicalHistory, patient=patient)
            serializer = MedicalHistoryUpdateSerializer(medical_history)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            raise NotFound('User not found')
        except Patient.DoesNotExist:
            logger.error(f"Patient profile for user {user_id} not found")
            raise NotFound('Patient profile not found')
        except MedicalHistory.DoesNotExist:
            logger.error(f"Medical history for patient {patient.id} not found")
            raise NotFound('Medical history not found')
        except Exception as e:
            logger.error(f"Error retrieving medical history: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve medical history'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            medical_history = get_object_or_404(MedicalHistory, patient=patient)
            serializer = MedicalHistoryUpdateSerializer(medical_history, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Medical history updated successfully for user {user_id}")
                return Response({
                    'status': 'success',
                    'message': 'Medical history updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Medical history update failed: {serializer.errors}")
                return Response({
                    'status': 'error',
                    'message': 'Update failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            raise NotFound('User not found')
        except Patient.DoesNotExist:
            logger.error(f"Patient profile for user {user_id} not found")
            raise NotFound('Patient profile not found')
        except MedicalHistory.DoesNotExist:
            logger.error(f"Medical history for patient {patient.id} not found")
            raise NotFound('Medical history not found')
        except Exception as e:
            logger.error(f"Error updating medical history: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            patient = user.patient_profile
            
            try:
                medical_history = MedicalHistory.objects.get(patient=patient)
                medical_history.delete()
                logger.info(f"Medical history deleted successfully for user {user_id}")
                
                return Response({
                    'status': 'success',
                    'message': 'Medical history deleted successfully'
                }, status=status.HTTP_200_OK)
                
            except MedicalHistory.DoesNotExist:
                logger.error(f"Medical history for patient {user_id} not found")
                return Response({
                    'status': 'error',
                    'message': 'Medical history not found'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found")
            return Response({
                'status': 'error',
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Patient.DoesNotExist:
            logger.error(f"Patient profile for user {user_id} not found")
            return Response({
                'status': 'error',
                'message': 'Patient profile not found'
            }, status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting medical history: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           APPOINTMENT VIEWS                                  ║
║ Handles all appointment-related operations including scheduling, viewing,    ║
║ and managing appointments.                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class UserAppointmentsView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role.name != 'PATIENT':
            return Response({"error": "Only patients can access this information"}, status=status.HTTP_403_FORBIDDEN)

        try:
            appointments = Appointment.objects.filter(patient=user)
            if not appointments.exists():
                return Response({"error": "No appointments found"}, status=status.HTTP_404_NOT_FOUND)
            
            response_data = AppointmentSerializer(appointments, many=True).data
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving appointments for user {user.id}: {str(e)}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAppointmentDetailView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        user = request.user
        if user.role.name != 'PATIENT':
            return Response({"error": "Only patients can access this information"}, status=status.HTTP_403_FORBIDDEN)

        try:
            appointment = Appointment.objects.get(id=appointment_id, patient=user)
            response_data = AppointmentSerializer(appointment).data
            return Response(response_data, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving appointment {appointment_id} for user {user.id}: {str(e)}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DoctorAvailableTimeSlotsView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        
        if not all([doctor_id, date_str]):
            return Response(
                {"error": "Both doctor_id and date parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get the user with role DOCTOR
            user = User.objects.get(id=doctor_id, role='DOCTOR')
            doctor = user.doctor_profile
            
            # Get all available time slots for the doctor on the given date
            available_slots = DoctorTimeSlot.objects.filter(
                doctor=doctor,
                date=date,
                is_available=True
            ).order_by('start_time')
            
            # If no slots exist for this date, generate them based on doctor's availability
            if not available_slots.exists():
                day_of_week = date.weekday()
                availabilities = doctor.availability.filter(
                    day_of_week=day_of_week,
                    is_available=True
                )
                
                new_slots = []
                for availability in availabilities:
                    current_time = availability.start_time
                    while current_time < availability.end_time:
                        end_time = (
                            datetime.combine(date, current_time) + 
                            timedelta(minutes=30)
                        ).time()
                        
                        if end_time <= availability.end_time:
                            new_slots.append(DoctorTimeSlot(
                                doctor=doctor,
                                date=date,
                                start_time=current_time,
                                end_time=end_time
                            ))
                        
                        current_time = end_time
                
                if new_slots:
                    DoctorTimeSlot.objects.bulk_create(new_slots)
                    available_slots = DoctorTimeSlot.objects.filter(
                        doctor=doctor,
                        date=date,
                        is_available=True
                    ).order_by('start_time')
            
            serializer = DoctorTimeSlotSerializer(available_slots, many=True)
            return Response({
                'status': 'success',
                'message': 'Available time slots retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Doctor not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving available time slots: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DoctorTimeSlotDetailView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, slot_id):
        try:
            # Fetch the time slot by ID
            time_slot = DoctorTimeSlot.objects.get(id=slot_id)
            serializer = DoctorTimeSlotDetailSerializer(time_slot)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except DoctorTimeSlot.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Time slot not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving time slot {slot_id}: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class DoctorClinicsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user_id = request.query_params.get('user_id')
        if not user_id:
            logger.warning("DoctorClinicsAPIView: Missing user_id parameter")
            return Response({'error': 'Missing user_id parameter'}, status=400)
        try:
            logger.debug(f"DoctorClinicsAPIView: Looking up user with id {user_id}")
            user = get_object_or_404(User, pk=user_id)
            logger.debug(f"DoctorClinicsAPIView: Found user: {user} with role {user.role.name}")
            if user.role.name != 'DOCTOR':
                logger.warning(f"DoctorClinicsAPIView: User with id {user_id} is not a doctor")
                return Response({'error': 'User is not a doctor'}, status=403)
            from appointment_management.models import DoctorTimeSlot
            doctor_profile = user.doctor_profile
            centers = DoctorTimeSlot.objects.filter(doctor=doctor_profile).values('center__id', 'center__name').distinct()
            clinics_data = [{'id': center['center__id'], 'name': center['center__name']} for center in centers]
            return Response({'clinics': clinics_data})
        except Http404:
            logger.warning(f"DoctorClinicsAPIView: User with user_id {user_id} not found")
            return Response({'error': 'Doctor not found'}, status=404)
        except Exception as e:
            logger.error(f"DoctorClinicsAPIView: Internal server error for user {user_id}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)

class AppointmentTypesView(APIView):
    def get(self, request):
        types = [{'value': choice[0], 'label': choice[1]} for choice in Appointment.APPOINTMENT_TYPES]
        return Response(types, status=status.HTTP_200_OK)


class AppointmentStatusView(APIView):
    def get(self, request):
        statuses = [{'value': choice[0], 'label': choice[1]} for choice in Appointment.STATUS_CHOICES]
        return Response(statuses, status=status.HTTP_200_OK)


class AppointmentPriorityView(APIView):
    def get(self, request):
        priorities = [{'value': choice[0], 'label': choice[1]} for choice in Appointment.PRIORITY_CHOICES]
        return Response(priorities, status=status.HTTP_200_OK)
        

class CreateAppointmentView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppointmentCreateSerializer(data=request.data)
        try:
            if serializer.is_valid():
                appointment = serializer.save(patient=request.user)
                
                # Update the DoctorTimeSlot to mark it as unavailable
                doctor_time_slot = appointment.time_slot
                doctor_time_slot.is_available = False
                doctor_time_slot.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except DoctorTimeSlot.DoesNotExist:
            return Response({"error": "Time slot does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return Response({"error": "Database error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              DOCTOR VIEWS                                    ║
║ Manages doctor-related operations including listings, profiles, and          ║
║ specialization information.                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class DoctorListView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    # Valid parameter mappings
    PARAM_MAPPINGS = {
        'specialization': {
            'model': Specialization,
            'filter_field': 'specializations__id'
        },
        'treatment_method': {
            'model': TreatmentMethodSpecialization,
            'filter_field': 'treatment_methods__id'
        },
        'body_area': {
            'model': BodyAreaSpecialization,
            'filter_field': 'body_areas__id'
        },
        'associated_condition': {
            'model': AssociatedConditionSpecialization,
            'filter_field': 'associated_conditions__id'
        }
    }

    def normalize_param_name(self, param_name):
        """Normalize parameter names to handle different formats"""
        return param_name.replace('-', '_')

    def validate_param_name(self, param_name):
        """Validate if the parameter name is valid"""
        normalized_name = self.normalize_param_name(param_name)
        if normalized_name not in self.PARAM_MAPPINGS:
            return False, f"Invalid parameter: '{param_name}'. Valid parameters are: {', '.join(self.PARAM_MAPPINGS.keys())}"
        return True, normalized_name

    def validate_single_param(self, param_name, param_value, model):
        """Validate a single filter parameter value"""
        try:
            param_id = int(param_value)
            if not model.objects.filter(id=param_id, is_active=True).exists():
                return None, f"Invalid {param_name} ID: {param_value} (ID does not exist)"
            return param_id, None
        except (ValueError, TypeError):
            return None, f"Invalid {param_name} parameter: {param_value} (must be an integer)"

    def get(self, request):
        try:
            # First, validate all parameters in the request
            unknown_params = []
            for param_name in request.query_params.keys():
                is_valid, _ = self.validate_param_name(param_name)
                if not is_valid:
                    unknown_params.append(param_name)
            
            if unknown_params:
                return Response({
                    'status': 'error',
                    'error': f"Unknown parameter(s): {', '.join(unknown_params)}",
                    'valid_parameters': list(self.PARAM_MAPPINGS.keys())
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check for any valid filter parameters
            filter_param = None
            filter_value = None
            
            for key, value in request.query_params.items():
                is_valid, normalized_key = self.validate_param_name(key)
                if is_valid:
                    filter_param = normalized_key
                    filter_value = value
                    break

            # If a filter parameter is found, validate and apply it
            if filter_param and filter_value:
                mapping = self.PARAM_MAPPINGS[filter_param]
                param_id, error = self.validate_single_param(
                    filter_param,
                    filter_value,
                    mapping['model']
                )

                if error:
                    return Response({
                        'status': 'error',
                        'error': error
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Get filtered doctors
                doctors = DoctorProfile.objects.select_related('user').prefetch_related(
                    'specializations',
                    'treatment_methods',
                    'body_areas',
                    'associated_conditions'
                ).filter(
                    user__role='DOCTOR',
                    user__is_active=True,
                    is_available=True,
                    **{mapping['filter_field']: param_id}
                ).distinct()    

                serializer = DoctorListSerializer(doctors, many=True)
                return Response({
                    'status': 'success',
                    'filter_applied': {
                        'parameter': filter_param,
                        'value': filter_value,
                        'id': param_id
                    },
                    'count': doctors.count(),
                    'results': serializer.data
                }, status=status.HTTP_200_OK)

            # If no filter parameters are provided, return all active doctors
            doctors = DoctorProfile.objects.select_related('user').prefetch_related(
                'specializations',
                'treatment_methods',
                'body_areas',
                'associated_conditions'
            ).filter(
                user__role='DOCTOR',
                user__is_active=True,
                is_available=True
            )
            
            serializer = DoctorListSerializer(doctors, many=True)
            return Response({
                'status': 'success',
                'filter_applied': None,
                'count': doctors.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error in doctor list view: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'error_details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorDetailView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, doctor_id):
        try:
            # Get the user with role DOCTOR
            user = get_object_or_404(User, id=doctor_id, role='DOCTOR', is_active=True)
            doctor = get_object_or_404(
                DoctorProfile.objects.select_related('user').prefetch_related(
                    'specializations',
                    'treatment_methods',
                    'body_areas',
                    'associated_conditions',
                    'availability',
                    'reviews__patient'
                ),
                user=user
            )
            
            serializer = DoctorDetailSerializer(doctor)
            return Response({
                'status': 'success',
                'message': 'Doctor details retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response(
                {"error": "Doctor not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"error": "Doctor profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving doctor details for user ID {doctor_id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            specializations = Specialization.objects.filter(is_active=True)
            serializer = SpecializationSerializer(specializations, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving specializations: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TreatmentMethodListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            treatments = TreatmentMethodSpecialization.objects.filter(is_active=True)
            serializer = TreatmentMethodSerializer(treatments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving treatment methods: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BodyAreaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            body_areas = BodyAreaSpecialization.objects.filter(is_active=True)
            serializer = BodyAreaSerializer(body_areas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving body areas: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssociatedConditionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            conditions = AssociatedConditionSpecialization.objects.filter(is_active=True)
            serializer = AssociatedConditionSerializer(conditions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving associated conditions: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


""" 
╔══════════════════════════════════════════════════════════════════════════════╗
║                              QUERY VIEWS                                     ║
║ Manages user queries and related operations for patient-doctor               ║
║ communication.                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

class PriorityChoicesView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        choices = [{'value': choice[0], 'display': choice[1]} for choice in Query.PRIORITY_CHOICES]
        serializer = ChoiceSerializer(choices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SourceChoicesView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        choices = [{'value': choice[0], 'display': choice[1]} for choice in Query.SOURCE_CHOICES]
        serializer = ChoiceSerializer(choices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StatusChoicesView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        choices = [{'value': choice[0], 'display': choice[1]} for choice in Query.STATUS_CHOICES]
        serializer = ChoiceSerializer(choices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class QueryTagListView(APIView):
    def get(self, request):
        try:
            tags = QueryTag.objects.all()
            serializer = QueryTagSerializer(tags, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "Tags not found"}, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return Response({"error": "Database error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserQueriesView(APIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            queries = Query.objects.filter(user=user)
            serializer = QuerySerializer(queries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return Response({"error": "Database error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        user = request.user
        data = request.data.copy()
        data['user'] = user.id  # Set the patient to the current user

        serializer = QuerySerializer(data=data)
        if serializer.is_valid():
            try:
                query = serializer.save()
                # Handle tags separately
                tags = data.get('tags', [])
                if tags:
                    query.tags.set(tags)
                
                # Handle attachments separately
                files = request.FILES.getlist('attachments')
                for file in files:
                    QueryAttachment.objects.create(query=query, file=file)
                
                return Response(QuerySerializer(query).data, status=status.HTTP_201_CREATED)
            except DatabaseError as e:
                logger.error(f"Database error: {str(e)}", exc_info=True)
                return Response({"error": "Database error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)