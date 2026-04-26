from django.urls import path

from .views import MarkAllNotificationsReadView, MyNotificationDetailView, MyNotificationListView


urlpatterns = [
    path("", MyNotificationListView.as_view(), name="notification-list"),
    path("mark-all-read/", MarkAllNotificationsReadView.as_view(), name="notification-mark-all-read"),
    path("<int:pk>/", MyNotificationDetailView.as_view(), name="notification-detail"),
]

