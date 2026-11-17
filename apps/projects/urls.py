from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list'),
    path('<int:pk>/', views.ProjectRetrieveUpdateDestroyView.as_view(), name='project-detail'),
    path('<int:pk>/dashboard/', views.ProjectDashboardView.as_view(), name='project-dashboard'),
    path('<int:pk>/recalculate/', views.RecalculateProjectView.as_view(), name='project-recalculate'),
    path('<int:pk>/members/', views.ProjectMembershipListView.as_view(), name='project-members'),
    path('<int:pk>/members/performance/', views.ProjectMemberPerformanceView.as_view(), name='project-member-performance'),
    path('<int:pk>/members/<int:membership_id>/', views.ProjectMembershipDeleteView.as_view(), name='project-member-delete'),
    path('<int:pk>/members/<int:membership_id>/role/', views.ProjectMembershipUpdateRoleView.as_view(), name='project-member-role'),
    path('<int:pk>/note/', views.ProjectNoteView.as_view(), name='project-note'),
    path('<int:pk>/holidays/', views.HolidayListCreateView.as_view(), name='project-holidays'),
    path('<int:pk>/holidays/<int:holiday_id>/', views.HolidayDestroyView.as_view(), name='project-holiday-delete'),
    path('<int:pk>/attachments/', views.ProjectAttachmentListCreateView.as_view(), name='project-attachments'),
    path('<int:pk>/attachments/<int:att_id>/', views.ProjectAttachmentUpdateDestroyView.as_view(), name='project-attachment-detail'),
    path('<int:pk>/folders/', views.FolderListCreateView.as_view(), name='project-folders'),
    path('<int:pk>/folders/<int:folder_id>/', views.FolderDestroyView.as_view(), name='project-folder-delete'),
    path('<int:pk>/folders/<int:folder_id>/download/', views.FolderDownloadView.as_view(), name='project-folder-download'),
]
