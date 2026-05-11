import pytest

from apps.appointments.handlers import (
    handle_payment_failed,
    handle_payment_succeeded,
    handle_slot_released,
)
from apps.appointments.models import AppointmentStatus

from .factories import make_appointment


@pytest.mark.django_db
def test_payment_succeeded_transitions_to_paid():
    appt = make_appointment()
    handle_payment_succeeded({"appointment_id": str(appt.id), "payment_id": "pi_1"})
    appt.refresh_from_db()
    assert appt.status == AppointmentStatus.PAID
    assert appt.payment_intent_id == "pi_1"


@pytest.mark.django_db
def test_payment_succeeded_idempotent_when_already_paid():
    appt = make_appointment(status=AppointmentStatus.PAID, payment_intent_id="pi_orig")
    handle_payment_succeeded({"appointment_id": str(appt.id), "payment_id": "pi_dup"})
    appt.refresh_from_db()
    assert appt.payment_intent_id == "pi_orig"


@pytest.mark.django_db
def test_payment_failed_marks_failed():
    appt = make_appointment()
    handle_payment_failed({"appointment_id": str(appt.id)})
    appt.refresh_from_db()
    assert appt.status == AppointmentStatus.FAILED


@pytest.mark.django_db
def test_slot_released_expires_pending_appointment():
    appt = make_appointment()
    handle_slot_released({"appointment_id": str(appt.id), "slot_id": str(appt.slot_id)})
    appt.refresh_from_db()
    assert appt.status == AppointmentStatus.EXPIRED


@pytest.mark.django_db
def test_handler_safe_when_appointment_missing():
    handle_payment_succeeded({"appointment_id": "00000000-0000-0000-0000-000000000000"})
