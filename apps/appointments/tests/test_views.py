import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.appointments.models import AppointmentStatus

from .factories import jwt_for, make_appointment


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_list_requires_auth(api):
    resp = api.get("/api/v1/appointments/")
    assert resp.status_code == 403  # DRF returns 403 for unauth on permission_classes


@pytest.mark.django_db
def test_patient_sees_only_their_appointments(api):
    me = uuid.uuid4()
    mine = make_appointment(patient_id=me)
    other = make_appointment()

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_for(me, 'patient')}")
    resp = api.get("/api/v1/appointments/")
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert str(mine.id) in ids
    assert str(other.id) not in ids


@pytest.mark.django_db
def test_create_appointment_happy_path(api):
    patient = uuid.uuid4()
    slot_id = uuid.uuid4()
    start = timezone.now() + timedelta(days=1)

    with patch("apps.appointments.services.ScheduleClient") as MockClient:
        MockClient.return_value.reserve_slot.return_value = {"slot_id": str(slot_id)}
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_for(patient, 'patient')}")
        resp = api.post(
            "/api/v1/appointments/",
            {
                "patient_id": str(patient),
                "doctor_id": str(uuid.uuid4()),
                "slot_id": str(slot_id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": (start + timedelta(minutes=30)).isoformat(),
            },
            format="json",
        )
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == AppointmentStatus.PENDING_PAYMENT


@pytest.mark.django_db
def test_cancel_appointment(api):
    me = uuid.uuid4()
    appt = make_appointment(patient_id=me)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_for(me, 'patient')}")
    resp = api.post(
        f"/api/v1/appointments/{appt.id}/cancel/",
        {"reason": "scheduling conflict"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == AppointmentStatus.CANCELLED


@pytest.mark.django_db
def test_status_update_requires_internal_token(api, settings):
    appt = make_appointment()
    # without internal token → 403
    resp = api.patch(
        f"/api/v1/appointments/{appt.id}/status/",
        {"status": AppointmentStatus.PAID},
        format="json",
    )
    assert resp.status_code == 403

    # with internal token → 200
    api.credentials(HTTP_X_INTERNAL_TOKEN=settings.INTERNAL_SHARED_TOKEN)
    resp = api.patch(
        f"/api/v1/appointments/{appt.id}/status/",
        {"status": AppointmentStatus.PAID, "payment_intent_id": "pi_test"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == AppointmentStatus.PAID


@pytest.mark.django_db
def test_health(api):
    resp = api.get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
