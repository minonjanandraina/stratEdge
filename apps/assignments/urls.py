from django.urls import path
from . import views

urlpatterns = [
    path('', views.AssignmentListCreateView.as_view(), name='assignment-list'),
    path('<int:assignment_id>/', views.AssignmentRetrieveUpdateDestroyView.as_view(), name='assignment-detail'),
    path('time-entries/', views.TimeEntryListCreateView.as_view(), name='time-entry-list'),
]
