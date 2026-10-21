from datetime import time

from django.core.management.base import BaseCommand

from bookings.models import Room, Slot


ROOMS = [
    {
        "name": "Meridian Boardroom",
        "capacity": 12,
        "price_per_hour": 350000,
        "facilities": ["4K display", "Video conference", "Whiteboard", "Coffee"],
        "image": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Cedar Studio",
        "capacity": 6,
        "price_per_hour": 180000,
        "facilities": ["55-inch display", "Whiteboard", "Natural light"],
        "image": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Orbit Huddle",
        "capacity": 4,
        "price_per_hour": 120000,
        "facilities": ["Monitor", "Video call", "Acoustic panels"],
        "image": "https://images.unsplash.com/photo-1517502884422-41eaead166d4?auto=format&fit=crop&w=1200&q=80",
    },
]


class Command(BaseCommand):
    help = "Create the sample rooms and time slots used by the booking experience."

    def handle(self, *args, **options):
        for room_data in ROOMS:
            room, created = Room.objects.update_or_create(name=room_data["name"], defaults=room_data)
            for hour in (9, 10, 11, 13, 14, 15, 16):
                Slot.objects.get_or_create(room=room, time=time(hour, 0))
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} {room.name}"))
