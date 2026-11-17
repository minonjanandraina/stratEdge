from django.urls import path
from . import views

urlpatterns = [
    path('', views.TaskListCreateView.as_view(), name='task-list'),
    path('<int:task_id>/', views.TaskRetrieveUpdateDestroyView.as_view(), name='task-detail'),
    path('<int:task_id>/progress/', views.ProgressUpdateView.as_view(), name='task-progress'),
    path('<int:task_id>/assignees/', views.TaskAssigneeListCreateView.as_view(), name='task-assignees'),
    path('<int:task_id>/assignees/<int:assignment_id>/', views.TaskAssigneeDestroyView.as_view(), name='task-assignee-delete'),
    path('<int:task_id>/attachments/', views.TaskAttachmentListCreateView.as_view(), name='task-attachments'),
    path('<int:task_id>/attachments/<int:att_id>/', views.TaskAttachmentDestroyView.as_view(), name='task-attachment-delete'),
    path('<int:task_id>/notes/', views.TaskNoteListCreateView.as_view(), name='task-notes'),
    path('reorder/', views.ReorderView.as_view(), name='task-reorder'),
    path('gantt/', views.GanttDataView.as_view(), name='task-gantt'),
    path('critical-path/', views.CriticalPathView.as_view(), name='task-critical-path'),
    path('dependencies/', views.DependencyListCreateView.as_view(), name='dependency-list'),
    path('dependencies/<int:dep_id>/', views.DependencyDestroyView.as_view(), name='dependency-delete'),
]
