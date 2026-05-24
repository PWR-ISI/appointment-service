from django.db import models
from django.utils import timezone

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('no-show', 'No Show'),
    )

    APPOINTMENT_TYPES = (
        ('consultation', 'Consultation'),
        ('checkup', 'Checkup'),
        ('follow-up', 'Follow-up'),
        ('procedure', 'Procedure'),
        ('urgent', 'Urgent'),
    )

    id = models.AutoField(primary_key=True)
    patient_id = models.IntegerField()
    doctor_id = models.IntegerField()
    appointment_date = models.DateTimeField()
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES, default='consultation')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['doctor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['appointment_date']),
        ]

    def __str__(self):
        return f"Appointment {self.id} - {self.appointment_date}"


class AppointmentNotes(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='medical_notes')
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    prescriptions = models.JSONField(default=list)
    vital_signs = models.JSONField(default=dict)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    created_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointment_notes'

    def __str__(self):
        return f"Notes for Appointment {self.appointment_id}"


class AppointmentHistory(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='history')
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by_id = models.IntegerField()
    change_reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appointment_history'
        ordering = ['-changed_at']

    def __str__(self):
        return f"History for Appointment {self.appointment_id}"
