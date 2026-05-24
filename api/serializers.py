from rest_framework import serializers
from .models import Appointment, AppointmentNotes, AppointmentHistory


class AppointmentNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentNotes
        fields = ('id', 'diagnosis', 'treatment', 'prescriptions', 'vital_signs', 'follow_up_required', 'follow_up_date', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentHistory
        fields = ('id', 'previous_status', 'new_status', 'change_reason', 'changed_at')
        read_only_fields = ('id', 'changed_at')


class AppointmentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('id', 'patient_id', 'doctor_id', 'appointment_date', 'appointment_type', 'status', 'location', 'created_at')
        read_only_fields = ('id', 'created_at')


class AppointmentDetailSerializer(serializers.ModelSerializer):
    medical_notes = AppointmentNotesSerializer(read_only=True)
    history = AppointmentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Appointment
        fields = ('id', 'patient_id', 'doctor_id', 'appointment_date', 'appointment_type', 'status', 'description', 'notes', 'location', 'reminder_sent', 'medical_notes', 'history', 'created_at', 'updated_at')
        read_only_fields = ('id', 'reminder_sent', 'medical_notes', 'history', 'created_at', 'updated_at')


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('patient_id', 'doctor_id', 'appointment_date', 'appointment_type', 'description', 'location')

    def validate_appointment_date(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError('Appointment date must be in the future')
        return value

    def create(self, validated_data):
        appointment = Appointment.objects.create(**validated_data)
        AppointmentNotes.objects.create(appointment=appointment, created_by_id=self.context['request'].user.id)
        return appointment


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('appointment_date', 'appointment_type', 'description', 'location', 'status')


class AppointmentStatusChangeSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=['scheduled', 'completed', 'cancelled', 'rescheduled', 'no-show'])
    reason = serializers.CharField(required=False, allow_blank=True)
