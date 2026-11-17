import datetime
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember
from apps.tasks.models import Task
from apps.resources.models import Resource
from .exporters import ExcelExporter, PDFExporter


class OverviewReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        tasks = project.tasks.filter(is_summary=False)
        kpi = project.kpis.first()

        return Response({
            'project_id': project.id,
            'project_name': project.name,
            'status': project.get_status_display(),
            'progress': project.progress,
            'tasks_summary': {
                'total': tasks.count(),
                'completed': tasks.filter(status='completed').count(),
                'in_progress': tasks.filter(status='in_progress').count(),
                'not_started': tasks.filter(status='not_started').count(),
                'overdue': tasks.filter(
                    planned_end__lt=datetime.date.today(),
                    percent_complete__lt=100,
                ).count(),
                'critical': tasks.filter(is_critical=True).count(),
            },
            'kpis': {
                'spi': float(kpi.spi) if kpi else None,
                'schedule_health': kpi.schedule_health if kpi else None,
            },
        })


class ResourceReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        resources = Resource.objects.filter(project=project).prefetch_related('assignments__time_entries')
        data = []
        for res in resources:
            assignments = res.assignments.all()
            data.append({
                'resource_id': res.id,
                'name': res.name,
                'type': res.get_resource_type_display(),
                'tasks_count': assignments.count(),
                'planned_work': sum(float(a.planned_work) for a in assignments),
                'actual_work': sum(float(a.actual_work) for a in assignments),
            })
        return Response(data)


class ExportExcelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        data = ExcelExporter().export(project)
        response = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        tz3 = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz3).strftime('%Y-%m-%d_%Hh%M')
        name = project.name.replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="{name}_{now}.xlsx"'
        return response


class ExportPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        data = PDFExporter().export(project)
        response = HttpResponse(data, content_type='application/pdf')
        tz3 = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz3).strftime('%Y-%m-%d_%Hh%M')
        name = project.name.replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="{name}_{now}.pdf"'
        return response
