import uuid
from datetime import timedelta

from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentStatus


def make_appointment(**overrides) -> Appointment:
    start = overrides.pop("scheduled_start", timezone.now() + timedelta(days=1))
    end = overrides.pop("scheduled_end", start + timedelta(minutes=30))
    defaults = {
        "patient_id": uuid.uuid4(),
        "doctor_id": uuid.uuid4(),
        "slot_id": uuid.uuid4(),
        "facility_id": uuid.uuid4(),
        "status": AppointmentStatus.PENDING_PAYMENT,
        "scheduled_start": start,
        "scheduled_end": end,
        "created_by_user_id": uuid.uuid4(),
    }
    defaults.update(overrides)
    return Appointment.objects.create(**defaults)


def jwt_for(user_id: str, role: str) -> str:
    """Build an unsigned JWT (header.payload.) for testing the stub middleware."""
    import base64
    import json

    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    body = json.dumps({"sub": str(user_id), "role": role}).encode()
    payload = base64.urlsafe_b64encode(body).rstrip(b"=").decode()
    return f"{header}.{payload}."
