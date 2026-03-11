from http import HTTPStatus

from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler


class APIError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def api_exception_handler(exc, context):
    if isinstance(exc, APIError):
        return Response({"error": exc.message}, status=exc.status_code)

    response = exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(exc, NotAuthenticated):
        response.data = {"error": "Authentication required."}
        return response

    if isinstance(exc, AuthenticationFailed):
        response.data = {"error": str(exc.detail)}
        return response

    if isinstance(exc, PermissionDenied):
        response.data = {"error": "Permission denied."}
        return response

    if response.status_code == HTTPStatus.NOT_FOUND:
        response.data = {"error": "Not found."}
        return response

    if isinstance(response.data, list):
        response.data = {"error": response.data[0]}
    elif "detail" in response.data:
        response.data = {"error": str(response.data["detail"])}

    return response
