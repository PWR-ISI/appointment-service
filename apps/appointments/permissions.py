from rest_framework.permissions import BasePermission


class IsOwnerOrStaff(BasePermission):
    """
    Allows access when the request actor is the appointment's patient,
    doctor, a receptionist/admin, or an internal service call.
    """

    def has_object_permission(self, request, view, obj):
        if getattr(request, "is_internal", False):
            return True
        role = getattr(request, "user_role", None)
        if role in ("admin", "receptionist"):
            return True
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False
        if role == "patient" and str(obj.patient_id) == str(user_id):
            return True
        if role == "doctor" and str(obj.doctor_id) == str(user_id):
            return True
        return False
