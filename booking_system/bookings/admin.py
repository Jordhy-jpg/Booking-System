from django.contrib import admin

from .models import Booking, Room, Slot


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "price_per_hour")


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("room", "time")
    list_filter = ("room",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("code", "room", "slot", "date", "name", "participants", "created_at")
    list_filter = ("room", "date")
    search_fields = ("code", "name", "email")
