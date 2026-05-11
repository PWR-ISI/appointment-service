import pytest

from apps.appointments.models import (
    ALLOWED_TRANSITIONS,
    AppointmentStatus,
    TERMINAL_STATUSES,
)


def test_terminal_statuses_have_no_transitions():
    for terminal in TERMINAL_STATUSES:
        assert terminal not in ALLOWED_TRANSITIONS


def test_pending_payment_can_become_paid_or_cancelled():
    transitions = ALLOWED_TRANSITIONS[AppointmentStatus.PENDING_PAYMENT]
    assert AppointmentStatus.PAID in transitions
    assert AppointmentStatus.CANCELLED in transitions
    assert AppointmentStatus.EXPIRED in transitions


def test_paid_cannot_go_back_to_pending():
    transitions = ALLOWED_TRANSITIONS[AppointmentStatus.PAID]
    assert AppointmentStatus.PENDING_PAYMENT not in transitions
