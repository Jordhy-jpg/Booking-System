from django.urls import path

from .views import BookingCreateView, RegisterView, RoomListView, SlotListView

urlpatterns = [
    path("rooms", RoomListView.as_view(), name="rooms"),
    path("rooms/", RoomListView.as_view()),
    path("slots", SlotListView.as_view(), name="slots"),
    path("slots/", SlotListView.as_view()),
    path("bookings", BookingCreateView.as_view(), name="bookings"),
    path("bookings/", BookingCreateView.as_view()),
    path("auth/register/", RegisterView.as_view(), name="register"),
]
