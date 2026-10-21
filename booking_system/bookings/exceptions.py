from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class BookingConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This time slot has just been booked. Please choose another time."
    default_code = "slot_unavailable"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    response.data = {"error": {"code": getattr(exc, "default_code", "validation_error"), "details": response.data}}
    return response
