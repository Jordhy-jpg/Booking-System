import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=120, unique=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_hour = models.PositiveIntegerField()
    facilities = models.JSONField(default=list)
    image = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Slot(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="slots")
    time = models.TimeField()

    class Meta:
        ordering = ["time"]
        constraints = [models.UniqueConstraint(fields=["room", "time"], name="unique_room_slot_time")]

    def __str__(self):
        return f"{self.room.name} - {self.time:%H:%M}"


class Booking(models.Model):
    code = models.CharField(max_length=12, unique=True, editable=False)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="bookings")
    date = models.DateField()
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=24)
    participants = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["room", "slot", "date"], name="unique_room_slot_booking_day")]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"BK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code
