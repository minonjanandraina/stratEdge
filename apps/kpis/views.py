from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectManager
from .models import ProjectKPI
from .serializers import ProjectKPISerializer


class KPILatestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        kpi = project.kpis.first()
        if not kpi or kpi.total_tasks == 0:
            return Response(status=204)
        return Response(ProjectKPISerializer(kpi).data)


class KPIHistoryView(generics.ListAPIView):
    serializer_class = ProjectKPISerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        return ProjectKPI.objects.filter(
            project_id=self.kwargs['project_id']
        ).order_by('-calculated_at')[:50]


class KPICalculateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        baseline = project.baselines.filter(is_active=True).first()
        if not baseline:
            return Response({'detail': 'Aucune baseline active. Créez une baseline d\'abord.'}, status=400)
        from .services import KPICalculator
        status_date = date.fromisoformat(
            request.data.get('status_date', str(date.today()))
        )
        kpi = KPICalculator(project, baseline, status_date).calculate()
        return Response(ProjectKPISerializer(kpi).data, status=201)


class EVMCurvesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        kpis = ProjectKPI.objects.filter(
            project_id=project_id
        ).order_by('status_date').values(
            'status_date', 'spi', 'sv'
        )
        return Response(list(kpis))
