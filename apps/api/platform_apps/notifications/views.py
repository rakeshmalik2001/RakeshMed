from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get("unread", "").strip().lower()
        if unread_only in {"1", "true", "yes"}:
            queryset = queryset.filter(is_read=False)
        return queryset


class MyNotificationDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        if "is_read" in request.data:
            notification.is_read = bool(request.data.get("is_read"))
            notification.read_at = timezone.now() if notification.is_read else None
            notification.save(update_fields=["is_read", "read_at"])
        return Response(self.get_serializer(notification).data)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"status": "ok", "updated": updated}, status=status.HTTP_200_OK)

