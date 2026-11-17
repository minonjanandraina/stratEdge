from django.urls import path
from . import views

urlpatterns = [
    path('', views.BaselineListCreateView.as_view(), name='baseline-list'),
    path('<int:baseline_id>/', views.BaselineRetrieveUpdateDestroyView.as_view(), name='baseline-detail'),
    path('<int:baseline_id>/set-active/', views.SetActiveBaselineView.as_view(), name='baseline-set-active'),
]
