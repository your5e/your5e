from django.db import connection
from knox.auth import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    def get(self, request):
        try:
            connection.ensure_connection()
        except Exception:
            return Response({"status": "error"}, status=503)
        return Response({"status": "ok"})


class AuthenticatedAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class PingView(AuthenticatedAPIView):
    def get(self, request):
        return Response({"username": request.user.username})
