from django.urls import path
from . import views

urlpatterns = [
    path('', views.MeetingListCreateView.as_view(), name='meeting-list'),
    path('<int:meeting_id>/', views.MeetingRetrieveUpdateDestroyView.as_view(), name='meeting-detail'),
    path('<int:meeting_id>/minutes/', views.MeetingMinuteView.as_view(), name='meeting-minutes'),
    path('<int:meeting_id>/decisions/', views.MeetingDecisionListCreateView.as_view(), name='meeting-decisions'),
    path('<int:meeting_id>/decisions/<int:decision_id>/', views.MeetingDecisionUpdateDestroyView.as_view(), name='meeting-decision-detail'),
]
