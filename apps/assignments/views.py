from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectContributor
from apps.tasks.models import Task
from .models import Assignment, TimeEntry
from .serializers import AssignmentSerializer, TimeEntrySerializer


class AssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_queryset(self):
        return Assignment.objects.filter(
            task__project_id=self.kwargs['project_id']
        ).select_related('task', 'resource__user')

    def perform_create(self, serializer):
        task = get_object_or_404(
            Task, pk=self.request.data.get('task'), project_id=self.kwargs['project_id']
        )
        serializer.save(task=task)


class AssignmentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_object(self):
        return get_object_or_404(
            Assignment,
            pk=self.kwargs['assignment_id'],
            task__project_id=self.kwargs['project_id'],
        )


class TimeEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = TimeEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_queryset(self):
        return TimeEntry.objects.filter(
            assignment__task__project_id=self.kwargs['project_id']
        ).select_related('assignment__task', 'assignment__resource')

    def perform_create(self, serializer):
        assignment = get_object_or_404(
            Assignment,
            pk=self.request.data.get('assignment'),
            task__project_id=self.kwargs['project_id'],
        )
        entry = serializer.save(assignment=assignment)
        # Update actual_work on assignment
        total = sum(
            float(e.hours) for e in assignment.time_entries.all()
        )
        assignment.actual_work = total
        assignment.save(update_fields=['actual_work'])
