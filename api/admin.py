from django.contrib import admin
from .models import Appointment, AppointmentNotes, AppointmentHistory


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_id', 'doctor_id', 'appointment_date', 'status', 'appointment_type')
    list_filter = ('status', 'appointment_type', 'appointment_date')
    search_fields = ('patient_id', 'doctor_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AppointmentNotes)
class AppointmentNotesAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'follow_up_required', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AppointmentHistory)
class AppointmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'previous_status', 'new_status', 'changed_at')
    readonly_fields = ('changed_at',)
