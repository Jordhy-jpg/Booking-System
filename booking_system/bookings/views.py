from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .exceptions import BookingConflict
from .models import Booking, Room, Slot
from .permissions import ReadOnlyOrAdmin
from .serializers import BookingHistorySerializer, BookingSerializer, RegisterSerializer, RoomSerializer, SlotSerializer


class CancellationWindowClosed(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The cancellation deadline has passed."
    default_code = "cancellation_closed"


class RoomListView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = (ReadOnlyOrAdmin,)


class SlotListView(generics.ListCreateAPIView):
    serializer_class = SlotSerializer
    permission_classes = (ReadOnlyOrAdmin,)

    def get_queryset(self):
        room_id = self.request.query_params.get("roomId")
        queryset = Slot.objects.select_related("room")
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        date = self.request.query_params.get("date")
        if date:
            taken = Booking.objects.filter(slot_id=OuterRef("pk"), date=date, cancelled_at__isnull=True)
            queryset = queryset.annotate(is_booked=Exists(taken))
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = SlotSerializer(queryset, many=True).data
        for item, slot in zip(data, queryset):
            item["isAvailable"] = not getattr(slot, "is_booked", False)
        return Response(data)


class BookingCreateView(generics.CreateAPIView):
    serializer_class = BookingSerializer
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                room = Room.objects.select_for_update().get(pk=serializer.validated_data["room"].pk)
                slot = Slot.objects.select_for_update().get(pk=serializer.validated_data["slot"].pk)
                if Booking.objects.filter(room=room, slot=slot, date=serializer.validated_data["date"], cancelled_at__isnull=True).exists():
                    raise BookingConflict()
                serializer.save(user=self.request.user if self.request.user.is_authenticated else None)
        except IntegrityError as exc:
            raise BookingConflict() from exc


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingHistorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("room", "slot")


class BookingCancelView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, code):
        booking = get_object_or_404(Booking.objects.filter(user=request.user), code=code)
        with transaction.atomic():
            Room.objects.select_for_update().get(pk=booking.room_id)
            Slot.objects.select_for_update().get(pk=booking.slot_id)
            booking = Booking.objects.select_for_update().get(pk=booking.pk, user=request.user)
            if booking.cancelled_at is None:
                if timezone.localdate() > booking.cancellation_deadline:
                    raise CancellationWindowClosed()
                booking.cancelled_at = timezone.now()
                booking.save(update_fields=("cancelled_at",))
        return Response(BookingHistorySerializer(booking).data, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "booking"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)
