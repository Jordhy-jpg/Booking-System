from datetime import date
import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Booking, Room, Slot


class RoomSerializer(serializers.ModelSerializer):
    pricePerHour = serializers.IntegerField(source="price_per_hour")

    class Meta:
        model = Room
        fields = ("id", "name", "capacity", "pricePerHour", "facilities", "image")


class SlotSerializer(serializers.ModelSerializer):
    roomId = serializers.IntegerField(source="room_id")
    isAvailable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Slot
        fields = ("id", "roomId", "time", "isAvailable")


class BookingSerializer(serializers.ModelSerializer):
    roomId = serializers.PrimaryKeyRelatedField(source="room", queryset=Room.objects.all())
    slotId = serializers.PrimaryKeyRelatedField(source="slot", queryset=Slot.objects.select_related("room").all())

    class Meta:
        model = Booking
        fields = ("code", "roomId", "slotId", "date", "name", "email", "phone", "participants", "created_at")
        read_only_fields = ("code", "created_at")
        # The view detects this inside a transaction, rather than before it.
        validators = []

    def validate_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Booking date cannot be in the past.")
        return value

    def validate_phone(self, value):
        cleaned = re.sub(r"[\s-]", "", value)
        if not re.fullmatch(r"\+?[0-9]{9,15}", cleaned):
            raise serializers.ValidationError("Enter a valid phone number (9-15 digits).")
        return cleaned

    def validate(self, attrs):
        room, slot = attrs["room"], attrs["slot"]
        if slot.room_id != room.id:
            raise serializers.ValidationError({"slotId": "The selected slot does not belong to this room."})
        if attrs["participants"] > room.capacity:
            raise serializers.ValidationError({"participants": f"This room holds up to {room.capacity} people."})
        return attrs


class BookingHistorySerializer(serializers.ModelSerializer):
    room = serializers.CharField(source="room.name")
    time = serializers.TimeField(source="slot.time", format="%H:%M")

    class Meta:
        model = Booking
        fields = ("code", "room", "date", "time", "participants", "created_at")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)
