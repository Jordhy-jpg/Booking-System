from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Booking, Room, Slot


class BookingApiTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name="Focus Room", capacity=4, price_per_hour=150000, facilities=[])
        self.slot = Slot.objects.create(room=self.room, time="09:00")
        self.client = APIClient()
        self.payload = {
            "roomId": self.room.id,
            "slotId": self.slot.id,
            "date": str(date.today() + timedelta(days=1)),
            "name": "Budi",
            "email": "budi@example.com",
            "phone": "081234567890",
            "participants": 3,
        }

    def test_creates_booking(self):
        response = self.client.post("/api/bookings", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["code"].startswith("BK-"))
        self.assertEqual(Booking.objects.count(), 1)

    def test_rejects_taken_slot(self):
        self.client.post("/api/bookings", self.payload, format="json")
        response = self.client.post("/api/bookings", self.payload, format="json")
        self.assertEqual(response.status_code, 409)

    def test_rejects_over_capacity(self):
        self.payload["participants"] = 5
        response = self.client.post("/api/bookings", self.payload, format="json")
        self.assertEqual(response.status_code, 422)

    def test_slots_report_availability_for_date(self):
        self.client.post("/api/bookings", self.payload, format="json")
        response = self.client.get(f"/api/slots?roomId={self.room.id}&date={self.payload['date']}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data[0]["isAvailable"])
