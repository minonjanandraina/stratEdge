from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResourceListCreateView.as_view(), name='resource-list'),
    path('<int:resource_id>/', views.ResourceRetrieveUpdateDestroyView.as_view(), name='resource-detail'),
    path('<int:resource_id>/utilization/', views.ResourceUtilizationView.as_view(), name='resource-utilization'),
    path('overallocations/', views.OverallocationView.as_view(), name='resource-overallocations'),
    path('level/', views.LevelResourcesView.as_view(), name='resource-level'),
]
