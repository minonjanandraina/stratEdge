from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('stream/', views.notification_stream, name='notification-stream'),
    path('mark-all-read/', views.mark_all_read, name='notification-mark-all-read'),
    path('<int:pk>/read/', views.mark_read, name='notification-mark-read'),
]
