from rest_framework import serializers
from django.contrib.auth import get_user_model
from appointment_management.models import Appointment, DoctorTimeSlot
from user_management.serializers import CustomUserSerializer
from django.utils import timezone

class DoctorTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorTimeSlot
        fields = ['id', 'date', 'start_time', 'end_time', 'is_available']

class DoctorTimeSlotDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorTimeSlot
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    patient = CustomUserSerializer()
    doctor = CustomUserSerializer()
    status = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    appointment_type = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = '__all__'

    def get_status(self, obj):
        return obj.get_status_display()

    def get_priority(self, obj):
        return obj.get_priority_display()

    def get_appointment_type(self, obj):
        return obj.get_appointment_type_display()
    

class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'