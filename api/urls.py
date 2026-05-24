from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, health_check

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointments')

urlpatterns = [
    path('health/', health_check, name='health'),
    path('', include(router.urls)),
]
