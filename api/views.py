from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from .models import Appointment, AppointmentNotes, AppointmentHistory
from .serializers import (
    AppointmentListSerializer, AppointmentDetailSerializer,
    AppointmentCreateSerializer, AppointmentUpdateSerializer,
    AppointmentStatusChangeSerializer, AppointmentNotesSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'appointment_type', 'patient_id', 'doctor_id']
    ordering_fields = ['appointment_date', 'created_at']
    ordering = ['-appointment_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        elif self.action == 'retrieve':
            return AppointmentDetailSerializer
        return AppointmentListSerializer

    def get_queryset(self):
        queryset = Appointment.objects.all()
        patient_id = self.request.query_params.get('patient_id')
        doctor_id = self.request.query_params.get('doctor_id')
        status_param = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if date_from:
            queryset = queryset.filter(appointment_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(appointment_date__lte=date_to)

        return queryset

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status == 'cancelled':
            return Response({'error': 'Appointment is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AppointmentStatusChangeSerializer(data=request.data)
        if serializer.is_valid():
            AppointmentHistory.objects.create(
                appointment=appointment,
                previous_status=appointment.status,
                new_status='cancelled',
                changed_by_id=request.user.id,
                change_reason=serializer.validated_data.get('reason', '')
            )
            appointment.status = 'cancelled'
            appointment.save()
            return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status == 'completed':
            return Response({'error': 'Appointment is already completed'}, status=status.HTTP_400_BAD_REQUEST)

        AppointmentHistory.objects.create(
            appointment=appointment,
            previous_status=appointment.status,
            new_status='completed',
            changed_by_id=request.user.id
        )
        appointment.status = 'completed'
        appointment.save()
        return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'put'])
    def notes(self, request, pk=None):
        appointment = self.get_object()
        try:
            notes = AppointmentNotes.objects.get(appointment=appointment)
        except AppointmentNotes.DoesNotExist:
            notes = AppointmentNotes.objects.create(appointment=appointment, created_by_id=request.user.id)

        if request.method == 'GET':
            serializer = AppointmentNotesSerializer(notes)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = AppointmentNotesSerializer(notes, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        appointment = self.get_object()
        history = AppointmentHistory.objects.filter(appointment=appointment)
        serializer = AppointmentHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        queryset = self.get_queryset().filter(
            status='scheduled',
            appointment_date__gte=timezone.now()
        )[:10]
        serializer = AppointmentListSerializer(queryset, many=True)
        return Response(serializer.data)
