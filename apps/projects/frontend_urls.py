from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardFrontView.as_view(), name='dashboard'),
    path('projects/', views.ProjectListFrontView.as_view(), name='project-list-front'),
    path('projects/new/', views.ProjectCreateFrontView.as_view(), name='project-create-front'),
    path('projects/<int:pk>/', views.ProjectDetailFrontView.as_view(), name='project-detail-front'),
]
