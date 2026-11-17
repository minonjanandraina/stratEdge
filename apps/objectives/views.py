from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectManager

from .models import Objective, Indicator
from .serializers import (
    ObjectiveListSerializer, ObjectiveDetailSerializer,
    ObjectiveTreeSerializer, IndicatorSerializer,
)


def _get_project(kwargs):
    return get_object_or_404(Project, pk=kwargs['project_id'])


class ObjectiveListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/projects/{id}/objectives/        → flat list of root objectives
    POST /api/v1/projects/{id}/objectives/        → create objective (PM only)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ObjectiveDetailSerializer
        return ObjectiveListSerializer

    def get_queryset(self):
        project = _get_project(self.kwargs)
        return Objective.objects.filter(
            project=project, parent=None
        ).prefetch_related('children', 'indicators', 'tasks').order_by('order')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['project'] = _get_project(self.kwargs)
        return ctx

    def perform_create(self, serializer):
        project = _get_project(self.kwargs)
        last = Objective.objects.filter(project=project, parent=None).order_by('order').last()
        order = (last.order + 1) if last else 0
        serializer.save(project=project, order=order)


class ObjectiveTreeView(APIView):
    """
    GET /api/v1/projects/{id}/objectives/tree/
    Returns the full recursive tree for the LogFrame view.
    """
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        roots = Objective.objects.filter(
            project=project, parent=None
        ).prefetch_related('children__children', 'indicators', 'tasks').order_by('order')
        return Response(ObjectiveTreeSerializer(roots, many=True, context={'request': request}).data)


class ObjectiveRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/projects/{id}/objectives/{obj_id}/
    PATCH  /api/v1/projects/{id}/objectives/{obj_id}/   (PM only)
    DELETE /api/v1/projects/{id}/objectives/{obj_id}/   (PM only)
    """
    serializer_class = ObjectiveDetailSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        return Objective.objects.filter(
            project_id=self.kwargs['project_id']
        ).prefetch_related('children', 'indicators', 'tasks')

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['obj_id'])

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['project'] = _get_project(self.kwargs)
        return ctx


class ObjectiveTaskLinkView(APIView):
    """
    POST   /api/v1/projects/{id}/objectives/{obj_id}/tasks/
           body: { "task_id": <int> }   → link a task
    DELETE /api/v1/projects/{id}/objectives/{obj_id}/tasks/{task_id}/
           → unlink a task
    """
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def _get_objective(self, obj_id, project_id):
        return get_object_or_404(Objective, pk=obj_id, project_id=project_id)

    def post(self, request, project_id, obj_id):
        from apps.tasks.models import Task
        objective = self._get_objective(obj_id, project_id)

        if objective.level != 'output':
            return Response(
                {'detail': 'Seuls les objectifs de niveau "output" peuvent être liés à des tâches.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_id = request.data.get('task_id')
        if not task_id:
            return Response({'detail': 'task_id est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        objective.tasks.add(task)
        return Response({'detail': 'Tâche liée avec succès.'}, status=status.HTTP_201_CREATED)

    def delete(self, request, project_id, obj_id, task_id):
        from apps.tasks.models import Task
        objective = self._get_objective(obj_id, project_id)
        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        objective.tasks.remove(task)
        return Response(status=status.HTTP_204_NO_CONTENT)


class IndicatorListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/projects/{id}/objectives/{obj_id}/indicators/
    POST /api/v1/projects/{id}/objectives/{obj_id}/indicators/  (PM only)
    """
    serializer_class = IndicatorSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        return Indicator.objects.filter(
            objective_id=self.kwargs['obj_id'],
            objective__project_id=self.kwargs['project_id'],
        )

    def perform_create(self, serializer):
        objective = get_object_or_404(
            Objective, pk=self.kwargs['obj_id'], project_id=self.kwargs['project_id']
        )
        serializer.save(objective=objective)


class IndicatorRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/projects/{id}/objectives/{obj_id}/indicators/{ind_id}/
    PATCH  …   (PM only)
    DELETE …   (PM only)
    """
    serializer_class = IndicatorSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        return Indicator.objects.filter(
            objective_id=self.kwargs['obj_id'],
            objective__project_id=self.kwargs['project_id'],
        )

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['ind_id'])
