from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .exceptions import BookingConflict
from .models import Booking, Room, Slot
from .permissions import ReadOnlyOrAdmin
from .serializers import BookingHistorySerializer, BookingSerializer, RegisterSerializer, RoomSerializer, SlotSerializer


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
            taken = Booking.objects.filter(slot_id=OuterRef("pk"), date=date)
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
                if Booking.objects.filter(room=room, slot=slot, date=serializer.validated_data["date"]).exists():
                    raise BookingConflict()
                serializer.save(user=self.request.user if self.request.user.is_authenticated else None)
        except IntegrityError as exc:
            raise BookingConflict() from exc


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingHistorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("room", "slot")


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
