import uuid

from django.db import models


class AppointmentStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Pending payment"
    PAID = "paid", "Paid"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    FAILED = "failed", "Failed"


TERMINAL_STATUSES = {
    AppointmentStatus.COMPLETED,
    AppointmentStatus.CANCELLED,
    AppointmentStatus.EXPIRED,
    AppointmentStatus.FAILED,
}


ALLOWED_TRANSITIONS = {
    AppointmentStatus.PENDING_PAYMENT: {
        AppointmentStatus.PAID,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.EXPIRED,
        AppointmentStatus.FAILED,
    },
    AppointmentStatus.PAID: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    },
}


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.UUIDField(db_index=True)
    doctor_id = models.UUIDField(db_index=True)
    slot_id = models.UUIDField(unique=True)
    facility_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=24,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING_PAYMENT,
        db_index=True,
    )
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    payment_intent_id = models.CharField(max_length=128, blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_by_user_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["patient_id", "status"]),
            models.Index(fields=["doctor_id", "scheduled_start"]),
        ]

    def __str__(self) -> str:
        return f"Appointment {self.id} ({self.status})"


class IdempotencyRecord(models.Model):
    """Caches a successful response keyed by the Idempotency-Key header."""
    key = models.CharField(max_length=128, primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]
