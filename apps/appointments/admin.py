from django.contrib import admin

from .models import Appointment, IdempotencyRecord


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient_id", "doctor_id", "status", "scheduled_start")
    list_filter = ("status",)
    search_fields = ("patient_id", "doctor_id", "slot_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("key", "appointment", "created_at")
    readonly_fields = ("created_at",)
