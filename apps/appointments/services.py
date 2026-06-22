"""Business logic for the Appointment aggregate. Keep views thin."""
import logging
import uuid
from typing import Optional
from uuid import UUID

from django.conf import settings
from django.db import transaction

from common.events import publish
from common.exceptions import InvalidTransition

from .client import ScheduleClient
from .models import (
    ALLOWED_TRANSITIONS,
    Appointment,
    AppointmentStatus,
    IdempotencyRecord,
    TERMINAL_STATUSES,
)

logger = logging.getLogger(__name__)


class AppointmentService:
    @staticmethod
    def _publish(event_type: str, appointment: Appointment, extra: Optional[dict] = None):
        payload = {
            "appointment_id": str(appointment.id),
            "slot_id": str(appointment.slot_id),
            "patient_id": str(appointment.patient_id),
            "doctor_id": str(appointment.doctor_id),
            "scheduled_start": appointment.scheduled_start.isoformat(),
            "scheduled_end": appointment.scheduled_end.isoformat(),
            "status": appointment.status,
        }
        if extra:
            payload.update(extra)
        publish(settings.APPOINTMENT_SNS_TOPIC_ARN, event_type, payload)

    @staticmethod
    @transaction.atomic
    def create(
        *,
        patient_id: UUID,
        doctor_id: UUID,
        slot_id: UUID,
        scheduled_start,
        scheduled_end,
        created_by_user_id: UUID,
        facility_id: Optional[UUID] = None,
        notes: str = "",
        idempotency_key: Optional[str] = None,
        client: Optional[ScheduleClient] = None,
        patient_email: str = "",
    ) -> Appointment:
        if idempotency_key:
            existing = IdempotencyRecord.objects.select_related("appointment").filter(
                key=idempotency_key
            ).first()
            if existing:
                return existing.appointment

        # Pre-generate the appointment id so schedule-service can track which
        # appointment owns the reservation. If reservation fails we never
        # persist the appointment row.
        appointment_id = uuid.uuid4()
        client = client or ScheduleClient()
        client.reserve_slot(slot_id, appointment_id=appointment_id)

        appointment = Appointment.objects.create(
            id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            facility_id=facility_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )

        if idempotency_key:
            IdempotencyRecord.objects.create(key=idempotency_key, appointment=appointment)

        AppointmentService._publish("appointment.created", appointment,
                                     extra={"patient_email": patient_email} if patient_email else None)
        return appointment

    @staticmethod
    @transaction.atomic
    def cancel(appointment_id: UUID, reason: str, actor_id: Optional[UUID]) -> Appointment:
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        if appointment.status in TERMINAL_STATUSES:
            raise InvalidTransition(
                f"Cannot cancel an appointment in status {appointment.status}."
            )
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        appointment.save(update_fields=["status", "cancellation_reason", "updated_at"])

        AppointmentService._publish(
            "appointment.cancelled",
            appointment,
            extra={"reason": reason, "actor_id": str(actor_id) if actor_id else None},
        )
        return appointment

    @staticmethod
    @transaction.atomic
    def transition(appointment_id: UUID, new_status: str, payment_intent_id: str = "") -> Appointment:
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)
        current = AppointmentStatus(appointment.status)
        target = AppointmentStatus(new_status)
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidTransition(
                f"Cannot transition from {current} to {target}."
            )
        appointment.status = target
        if payment_intent_id:
            appointment.payment_intent_id = payment_intent_id
        appointment.save(
            update_fields=["status", "payment_intent_id", "updated_at"]
        )

        event_map = {
            AppointmentStatus.PAID: "appointment.paid",
            AppointmentStatus.COMPLETED: "appointment.completed",
            AppointmentStatus.CANCELLED: "appointment.cancelled",
            AppointmentStatus.EXPIRED: "appointment.expired",
            AppointmentStatus.FAILED: "appointment.failed",
        }
        event = event_map.get(target)
        if event:
            AppointmentService._publish(event, appointment)
        return appointment
