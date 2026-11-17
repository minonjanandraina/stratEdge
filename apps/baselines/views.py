from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectManager
from apps.tasks.models import Task
from apps.assignments.models import Assignment
from .models import Baseline, BaselineTask
from .serializers import BaselineSerializer


class BaselineListCreateView(generics.ListCreateAPIView):
    serializer_class = BaselineSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_queryset(self):
        return Baseline.objects.filter(project_id=self.kwargs['project_id'])

    @transaction.atomic
    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        baseline = serializer.save(project=project, created_by=self.request.user)
        # Snapshot all tasks
        tasks = Task.objects.filter(project=project, is_summary=False)
        bt_list = []
        for task in tasks:
            bt_list.append(BaselineTask(
                baseline=baseline,
                task=task,
                planned_start=task.planned_start,
                planned_end=task.planned_end,
                planned_duration=task.planned_duration,
                planned_work=float(task.planned_duration or 1) * 8,
                percent_complete=task.percent_complete,
            ))
        BaselineTask.objects.bulk_create(bt_list)


class BaselineRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BaselineSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_object(self):
        return get_object_or_404(
            Baseline,
            pk=self.kwargs['baseline_id'],
            project_id=self.kwargs['project_id'],
        )


class SetActiveBaselineView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def post(self, request, project_id, baseline_id):
        baseline = get_object_or_404(Baseline, pk=baseline_id, project_id=project_id)
        Baseline.objects.filter(project_id=project_id).update(is_active=False)
        baseline.is_active = True
        baseline.save(update_fields=['is_active'])
        return Response({'detail': f'Baseline "{baseline.name}" définie comme référence.'})
