from django.urls import path
from . import views

urlpatterns = [
    # Objectives
    path('',
         views.ObjectiveListCreateView.as_view(),
         name='objective-list-create'),

    path('tree/',
         views.ObjectiveTreeView.as_view(),
         name='objective-tree'),

    path('<int:obj_id>/',
         views.ObjectiveRetrieveUpdateDestroyView.as_view(),
         name='objective-detail'),

    # Task links (output level only)
    path('<int:obj_id>/tasks/',
         views.ObjectiveTaskLinkView.as_view(),
         name='objective-task-link'),

    path('<int:obj_id>/tasks/<int:task_id>/',
         views.ObjectiveTaskLinkView.as_view(),
         name='objective-task-unlink'),

    # Indicators (IOV)
    path('<int:obj_id>/indicators/',
         views.IndicatorListCreateView.as_view(),
         name='indicator-list-create'),

    path('<int:obj_id>/indicators/<int:ind_id>/',
         views.IndicatorRetrieveUpdateDestroyView.as_view(),
         name='indicator-detail'),
]
