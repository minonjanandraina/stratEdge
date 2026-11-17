from django.urls import path
from .views import DiscussionRoomView, FileUploadView

urlpatterns = [
    path('', DiscussionRoomView.as_view(), name='discussion-room'),
    path('upload/', FileUploadView.as_view(), name='discussion-upload'),
]
