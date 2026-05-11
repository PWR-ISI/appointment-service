from django.utils import timezone
from rest_framework import serializers

from .models import Appointment, AppointmentStatus


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient_id",
            "doctor_id",
            "slot_id",
            "facility_id",
            "status",
            "scheduled_start",
            "scheduled_end",
            "payment_intent_id",
            "cancellation_reason",
            "notes",
            "created_by_user_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    doctor_id = serializers.UUIDField()
    slot_id = serializers.UUIDField()
    facility_id = serializers.UUIDField(required=False, allow_null=True)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError("scheduled_end must be after scheduled_start.")
        if attrs["scheduled_start"] < timezone.now():
            raise serializers.ValidationError("scheduled_start must be in the future.")
        return attrs


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AppointmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AppointmentStatus.choices)
    payment_intent_id = serializers.CharField(required=False, allow_blank=True, default="")
