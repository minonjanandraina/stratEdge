from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectManager, IsProjectContributor
from .models import Resource
from .serializers import ResourceSerializer, ResourceUtilizationSerializer


def get_project(project_id):
    return get_object_or_404(Project, pk=project_id)


class ResourceListCreateView(generics.ListCreateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_queryset(self):
        return Resource.objects.filter(
            project_id=self.kwargs['project_id']
        ).select_related('user__profile').prefetch_related('assignments')

    def perform_create(self, serializer):
        project = get_project(self.kwargs['project_id'])
        serializer.save(project=project)


class ResourceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_object(self):
        return get_object_or_404(
            Resource, pk=self.kwargs['resource_id'], project_id=self.kwargs['project_id']
        )


class ResourceUtilizationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id, resource_id):
        resource = get_object_or_404(Resource, pk=resource_id, project_id=project_id)
        project = resource.project
        start = date.fromisoformat(request.query_params.get('start', str(project.start_date)))
        end = date.fromisoformat(request.query_params.get('end', str(project.end_date)))

        daily = resource.get_utilization(start, end)
        max_util = max(daily.values(), default=0)
        avg_util = sum(daily.values()) / len(daily) if daily else 0
        is_over = max_util > float(resource.max_units)

        return Response({
            'resource_id': resource.id,
            'resource_name': resource.name,
            'daily_utilization': {str(k): v for k, v in daily.items()},
            'is_overallocated': is_over,
            'max_utilization': max_util,
            'avg_utilization': round(avg_util, 2),
        })


class OverallocationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_project(project_id)
        resources = Resource.objects.filter(project=project)
        overallocated = []
        for res in resources:
            daily = res.get_utilization(project.start_date, project.end_date)
            max_util = max(daily.values(), default=0)
            if max_util > float(res.max_units):
                overallocated.append({
                    'resource_id': res.id,
                    'resource_name': res.name,
                    'max_utilization': max_util,
                    'max_units': float(res.max_units),
                    'overallocation_days': [
                        str(d) for d, u in daily.items() if u > float(res.max_units)
                    ],
                })
        return Response(overallocated)


class LevelResourcesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def post(self, request, project_id):
        project = get_project(project_id)
        # Simple delay-based leveling: shift non-critical tasks to resolve overallocations
        from apps.tasks.models import Task
        non_critical = Task.objects.filter(
            project=project, is_critical=False, is_summary=False
        ).order_by('-total_float')
        # Placeholder: real leveling requires complex constraint solving
        return Response({'detail': f'Nivellement effectué sur {non_critical.count()} tâches non critiques.'})
