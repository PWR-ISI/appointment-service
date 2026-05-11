import uuid
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentStatus
from apps.appointments.services import AppointmentService
from common.exceptions import InvalidTransition, SlotUnavailable

from .factories import make_appointment


@pytest.mark.django_db
def test_create_calls_schedule_and_persists():
    client = MagicMock()
    client.reserve_slot.return_value = {"slot_id": str(uuid.uuid4()), "status": "reserved"}
    patient_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    slot_id = uuid.uuid4()
    start = timezone.now() + timedelta(days=1)
    end = start + timedelta(minutes=30)

    appt = AppointmentService.create(
        patient_id=patient_id,
        doctor_id=doctor_id,
        slot_id=slot_id,
        scheduled_start=start,
        scheduled_end=end,
        created_by_user_id=patient_id,
        client=client,
    )

    assert Appointment.objects.filter(id=appt.id).exists()
    assert appt.status == AppointmentStatus.PENDING_PAYMENT
    client.reserve_slot.assert_called_once()


@pytest.mark.django_db
def test_create_rolls_back_when_slot_unavailable():
    client = MagicMock()
    client.reserve_slot.side_effect = SlotUnavailable("Slot is taken.")
    patient_id = uuid.uuid4()
    start = timezone.now() + timedelta(days=1)

    with pytest.raises(SlotUnavailable):
        AppointmentService.create(
            patient_id=patient_id,
            doctor_id=uuid.uuid4(),
            slot_id=uuid.uuid4(),
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=30),
            created_by_user_id=patient_id,
            client=client,
        )

    assert Appointment.objects.count() == 0


@pytest.mark.django_db
def test_cancel_marks_cancelled_and_records_reason():
    appt = make_appointment()
    actor = uuid.uuid4()

    updated = AppointmentService.cancel(appt.id, reason="patient changed mind", actor_id=actor)

    assert updated.status == AppointmentStatus.CANCELLED
    assert updated.cancellation_reason == "patient changed mind"


@pytest.mark.django_db
def test_cancel_rejected_when_already_terminal():
    appt = make_appointment(status=AppointmentStatus.COMPLETED)
    with pytest.raises(InvalidTransition):
        AppointmentService.cancel(appt.id, reason="x", actor_id=None)


@pytest.mark.django_db
def test_transition_pending_to_paid_succeeds():
    appt = make_appointment()
    updated = AppointmentService.transition(appt.id, AppointmentStatus.PAID, payment_intent_id="pi_1")
    assert updated.status == AppointmentStatus.PAID
    assert updated.payment_intent_id == "pi_1"


@pytest.mark.django_db
def test_transition_rejected_for_invalid_jump():
    appt = make_appointment()
    with pytest.raises(InvalidTransition):
        AppointmentService.transition(appt.id, AppointmentStatus.COMPLETED)
