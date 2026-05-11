"""
SQS event handlers for appointment-service.

The consume_events command looks up an event_type here and invokes the
matching handler. Handlers should be idempotent: SQS may redeliver, and the
same payment.succeeded event might land more than once.
"""
import logging

from .models import Appointment, AppointmentStatus
from .services import AppointmentService

logger = logging.getLogger(__name__)


def _appointment_or_none(appointment_id):
    try:
        return Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found; ignoring event.", appointment_id)
        return None


def handle_payment_succeeded(payload: dict, envelope: dict = None):
    appointment_id = payload.get("appointment_id")
    payment_intent_id = payload.get("payment_id") or payload.get("payment_intent_id") or ""
    appt = _appointment_or_none(appointment_id)
    if not appt:
        return
    if appt.status != AppointmentStatus.PENDING_PAYMENT:
        logger.info("Appointment %s already in %s; skipping payment.succeeded.", appt.id, appt.status)
        return
    AppointmentService.transition(
        appointment_id=appt.id,
        new_status=AppointmentStatus.PAID,
        payment_intent_id=payment_intent_id,
    )


def handle_payment_failed(payload: dict, envelope: dict = None):
    appointment_id = payload.get("appointment_id")
    appt = _appointment_or_none(appointment_id)
    if not appt:
        return
    if appt.status != AppointmentStatus.PENDING_PAYMENT:
        return
    AppointmentService.transition(appointment_id=appt.id, new_status=AppointmentStatus.FAILED)


def handle_slot_released(payload: dict, envelope: dict = None):
    """When schedule-service emits slot.released, expire the pending appointment."""
    appointment_id = payload.get("appointment_id")
    if not appointment_id:
        return
    appt = _appointment_or_none(appointment_id)
    if not appt or appt.status != AppointmentStatus.PENDING_PAYMENT:
        return
    AppointmentService.transition(appointment_id=appt.id, new_status=AppointmentStatus.EXPIRED)


HANDLERS = {
    "payment.succeeded": handle_payment_succeeded,
    "payment.failed": handle_payment_failed,
    "slot.released": handle_slot_released,
}
