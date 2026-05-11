import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from common.auth import IsAuthenticated, IsInternal, IsPatientOrReceptionist

from .models import Appointment, AppointmentStatus
from .permissions import IsOwnerOrStaff
from .serializers import (
    AppointmentCancelSerializer,
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AppointmentStatusUpdateSerializer,
)
from .services import AppointmentService

logger = logging.getLogger(__name__)


class AppointmentViewSet(ViewSet):
    """
    Exposes the Appointment HTTP surface. Logic lives in AppointmentService
    so views stay thin and easy to test.
    """

    lookup_field = "pk"

    def get_permissions(self):
        if self.action == "create":
            return [IsPatientOrReceptionist()]
        if self.action == "update_status":
            return [IsInternal()]
        return [IsAuthenticated()]

    # --- helpers ---
    def _get_object(self, pk) -> Appointment:
        return Appointment.objects.get(pk=pk)

    def _check_object_perm(self, request, obj):
        perm = IsOwnerOrStaff()
        if not perm.has_object_permission(request, self, obj):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

    # --- endpoints ---
    def list(self, request):
        qs = Appointment.objects.all()
        role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if role == "patient":
            qs = qs.filter(patient_id=user_id)
        elif role == "doctor":
            qs = qs.filter(doctor_id=user_id)
        else:
            # receptionists/admin/internal can filter explicitly.
            patient_id = request.query_params.get("patient_id")
            doctor_id = request.query_params.get("doctor_id")
            if patient_id:
                qs = qs.filter(patient_id=patient_id)
            if doctor_id:
                qs = qs.filter(doctor_id=doctor_id)

        serializer = AppointmentSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            appt = self._get_object(pk)
        except Appointment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self._check_object_perm(request, appt)
        return Response(AppointmentSerializer(appt).data)

    def create(self, request):
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key")
        appointment = AppointmentService.create(
            **serializer.validated_data,
            created_by_user_id=request.user_id or serializer.validated_data["patient_id"],
            idempotency_key=idempotency_key,
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        try:
            appt = self._get_object(pk)
        except Appointment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        self._check_object_perm(request, appt)
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = AppointmentService.cancel(
            appointment_id=appt.id,
            reason=serializer.validated_data.get("reason", ""),
            actor_id=getattr(request, "user_id", None),
        )
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        try:
            appt = self._get_object(pk)
        except Appointment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AppointmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = AppointmentService.transition(
            appointment_id=appt.id,
            new_status=serializer.validated_data["status"],
            payment_intent_id=serializer.validated_data.get("payment_intent_id", ""),
        )
        return Response(AppointmentSerializer(appointment).data)
