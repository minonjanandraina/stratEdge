from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Project, ProjectMembership, Holiday, Attachment, Folder, ProjectSettings, Note
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer,
    ProjectMembershipSerializer, HolidaySerializer, AttachmentSerializer, FolderSerializer,
    NoteSerializer,
)
from .permissions import IsProjectMember, IsProjectManager, IsProjectContributor, IsProjectAdmin


# ─── API Views ────────────────────────────────────────────────────────────────

class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'name']

    def get_queryset(self):
        user = self.request.user
        settings = ProjectSettings.get()
        if user.is_staff and settings.admin_see_all_projects:
            return Project.objects.select_related('manager').prefetch_related('memberships')
        return Project.objects.filter(
            memberships__user=user
        ).select_related('manager').prefetch_related('memberships').distinct()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectDetailSerializer
        return ProjectListSerializer


class ProjectRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), IsProjectAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return Project.objects.select_related('manager').prefetch_related(
            'memberships__user__profile', 'holidays'
        )


class ProjectDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)

        latest_kpi = project.kpis.first()
        from apps.kpis.serializers import ProjectKPISerializer
        kpi_data = ProjectKPISerializer(latest_kpi).data if latest_kpi else None

        return Response({
            'project': ProjectDetailSerializer(project, context={'request': request}).data,
            'kpis': kpi_data,
            'progress': project.progress,
        })


class RecalculateProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)

        from apps.tasks.services import recalculate_schedule
        from apps.kpis.tasks import recalculate_project_kpis
        recalculate_schedule(project)
        recalculate_project_kpis.delay(project.id)
        return Response({'detail': 'Recalcul terminé.'})


class ProjectMembershipListView(generics.ListCreateAPIView):
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_queryset(self):
        return ProjectMembership.objects.filter(
            project_id=self.kwargs['pk']
        ).select_related('user__profile')

    def perform_create(self, serializer):
        from apps.projects.utils import is_project_locked, set_project_manager
        from rest_framework.exceptions import PermissionDenied
        project = get_object_or_404(Project, pk=self.kwargs['pk'])
        if is_project_locked(project):
            raise PermissionDenied('Ce projet est verrouillé (statut terminé ou annulé).')
        membership = serializer.save(project=project)

        if membership.role == 'pm':
            set_project_manager(project, membership.user)

        # Notification #8 — Ajout au projet (interne + email)
        from apps.notifications.utils import notify
        notify(
            user=membership.user,
            notif_type='member_added',
            title=f'Vous avez été ajouté(e) au projet : {project.name}',
            message=(
                f'Vous avez été ajouté(e) au projet "{project.name}" '
                f'en tant que {membership.get_role_display()}.'
            ),
            project=project,
            send_email=True,
        )


class ProjectMembershipDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]
    queryset = ProjectMembership.objects.all()
    lookup_url_kwarg = 'membership_id'

    def perform_destroy(self, instance):
        from apps.projects.utils import clear_project_manager
        project, user = instance.project, instance.user
        instance.delete()
        clear_project_manager(project, user)


class ProjectMembershipUpdateRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, membership_id):
        if not request.user.is_staff:
            return Response({'detail': 'Réservé à l\'administrateur.'}, status=403)
        membership = get_object_or_404(ProjectMembership, pk=membership_id, project_id=pk)
        role = request.data.get('role')
        if role not in dict(ProjectMembership.ROLE_CHOICES):
            return Response({'detail': 'Rôle invalide.'}, status=400)
        membership.role = role
        membership.save(update_fields=['role'])

        if role == 'pm':
            from apps.projects.utils import set_project_manager
            set_project_manager(membership.project, membership.user)
        else:
            from apps.projects.utils import clear_project_manager
            clear_project_manager(membership.project, membership.user)

        return Response({'id': membership.id, 'role': membership.role})


class ProjectMemberPerformanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, pk):
        from django.utils import timezone
        from apps.resources.models import Resource
        from apps.assignments.models import Assignment

        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        today = timezone.now().date()

        qs = project.memberships.select_related('user')

        result = []
        for membership in qs:
            user = membership.user
            full_name = user.get_full_name() or user.username
            parts = (full_name or '?').split()
            initials = ''.join(p[0] for p in parts[:2]).upper() or '?'

            assignments = Assignment.objects.filter(
                resource__project=project, resource__user=user,
                task__is_summary=False,
            ).select_related('task')

            tasks = [a.task for a in assignments]
            total = len(tasks)

            if total == 0:
                result.append({
                    'user_id': user.id, 'name': full_name, 'initials': initials,
                    'role': membership.role,
                    'tasks_total': 0, 'tasks_completed': 0,
                    'tasks_in_progress': 0, 'tasks_overdue': 0,
                    'avg_progress': 0, 'planned_work': 0, 'actual_work': 0,
                    'health': 'gray',
                })
                continue

            completed   = sum(1 for t in tasks if t.status == 'completed')
            in_progress = sum(1 for t in tasks if t.status == 'in_progress')
            overdue     = sum(1 for t in tasks
                              if t.planned_end < today
                              and t.status not in ('completed', 'cancelled'))
            avg_progress = sum(float(t.percent_complete) for t in tasks) / total
            planned_work = sum(float(a.planned_work) for a in assignments)
            actual_work  = sum(float(a.actual_work)  for a in assignments)

            if overdue >= total / 2:
                health = 'red'
            elif overdue > 0 or avg_progress < 40:
                health = 'orange'
            else:
                health = 'green'

            result.append({
                'user_id': user.id, 'name': full_name, 'initials': initials,
                'role': membership.role,
                'tasks_total': total, 'tasks_completed': completed,
                'tasks_in_progress': in_progress, 'tasks_overdue': overdue,
                'avg_progress': round(avg_progress, 1),
                'planned_work': round(planned_work, 1),
                'actual_work': round(actual_work, 1),
                'health': health,
            })

        return Response(result)


class HolidayListCreateView(generics.ListCreateAPIView):
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_queryset(self):
        return Holiday.objects.filter(project_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.kwargs['pk'])
        serializer.save(project=project)


class HolidayDestroyView(generics.DestroyAPIView):
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_queryset(self):
        return Holiday.objects.filter(project_id=self.kwargs['pk'])

    def get_object(self):
        return get_object_or_404(
            Holiday, pk=self.kwargs['holiday_id'], project_id=self.kwargs['pk']
        )


# ─── Frontend Views ───────────────────────────────────────────────────────────

class ProjectListFrontView(LoginRequiredMixin, ListView):
    template_name = 'projects/list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        user = self.request.user
        settings = ProjectSettings.get()
        if user.is_staff and settings.admin_see_all_projects:
            return Project.objects.select_related('manager').all()
        return Project.objects.filter(memberships__user=user).select_related('manager').distinct()

    def get_context_data(self, **kwargs):
        from collections import defaultdict
        from django.utils import timezone
        from apps.assignments.models import Assignment

        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        projects = list(ctx['projects'])
        today = timezone.now().date()
        project_ids = [p.id for p in projects]

        assigned = list(Assignment.objects.filter(
            resource__user=user,
            task__project_id__in=project_ids,
            task__is_summary=False,
        ).values('task__project_id', 'task__status',
                 'task__percent_complete', 'task__planned_end'))

        raw = defaultdict(list)
        for a in assigned:
            raw[a['task__project_id']].append(a)

        all_pcts = []
        my_completed = my_overdue = 0

        for p in projects:
            tasks = raw.get(p.id, [])
            total = len(tasks)
            completed = sum(1 for t in tasks if t['task__status'] == 'completed')
            overdue = sum(1 for t in tasks
                         if t['task__planned_end'] < today
                         and t['task__status'] not in ('completed', 'cancelled'))
            avg_pct = sum(float(t['task__percent_complete']) for t in tasks) / total if total else 0

            p.my_total = total
            p.my_completed = completed
            p.my_overdue = overdue
            p.my_pct = round(avg_pct, 1)

            all_pcts.extend(float(t['task__percent_complete']) for t in tasks)
            my_completed += completed
            my_overdue += overdue

        ctx['my_total_tasks'] = len(all_pcts)
        ctx['my_completed_tasks'] = my_completed
        ctx['my_overdue_tasks'] = my_overdue
        ctx['my_avg_pct'] = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0
        ctx['global_avg_progress'] = round(
            sum(float(p.progress) for p in projects) / len(projects), 1
        ) if projects else 0
        ctx['projects_count'] = len(projects)
        return ctx


class ProjectDetailFrontView(LoginRequiredMixin, DetailView):
    template_name = 'projects/detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Project.objects.all()
        return Project.objects.filter(memberships__user=user).distinct()

    def get_context_data(self, **kwargs):
        from apps.projects.utils import is_project_locked
        ctx = super().get_context_data(**kwargs)
        ctx['current_project'] = self.object
        user = self.request.user
        ctx['is_pm'] = (
            self.object.manager == user
            or user.is_staff
            or ProjectMembership.objects.filter(project=self.object, user=user).exists()
        )
        ctx['project_locked'] = is_project_locked(self.object)
        p = self.object
        ctx['project_edit_data'] = {
            'name': p.name,
            'description': p.description or '',
            'status': p.status,
            'start_date': str(p.start_date) if p.start_date else '',
            'end_date': str(p.end_date) if p.end_date else '',
            'working_hours_per_day': p.working_hours_per_day or 8,
            'color': p.color or '',
        }
        return ctx


class ProjectCreateFrontView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'projects/form.html'
    fields = ['name', 'description', 'status', 'start_date', 'end_date', 'color']
    success_url = reverse_lazy('project-list-front')

    def form_valid(self, form):
        form.instance.manager = self.request.user
        response = super().form_valid(form)
        ProjectMembership.objects.get_or_create(
            project=self.object, user=self.request.user, defaults={'role': 'pm'}
        )
        return response


class ProjectAttachmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]
    parser_classes = [MultiPartParser, FormParser]

    def _get_project(self, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(self.request, project)
        return project

    def get(self, request, pk):
        project = self._get_project(pk)
        attachments = project.attachments.select_related('uploaded_by')
        return Response(AttachmentSerializer(attachments, many=True, context={'request': request}).data)

    def post(self, request, pk):
        project = self._get_project(pk)
        f = request.FILES.get('file')
        if not f:
            return Response({'file': 'Ce champ est obligatoire.'}, status=400)
        folder_id = request.data.get('folder_id') or None
        folder = None
        if folder_id:
            folder = get_object_or_404(Folder, pk=folder_id, project=project)
        att = Attachment.objects.create(
            project=project, file=f, folder=folder,
            name=request.data.get('name', f.name),
            uploaded_by=request.user, size=f.size,
        )
        return Response(AttachmentSerializer(att, context={'request': request}).data, status=201)


class ProjectAttachmentUpdateDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def _get_att(self, request, pk, att_id):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        return get_object_or_404(Attachment, pk=att_id, project=project), project

    def patch(self, request, pk, att_id):
        att, project = self._get_att(request, pk, att_id)
        folder_id = request.data.get('folder_id')
        if 'folder_id' in request.data:
            att.folder = get_object_or_404(Folder, pk=folder_id, project=project) if folder_id else None
            att.save(update_fields=['folder'])
        return Response(AttachmentSerializer(att, context={'request': request}).data)

    def delete(self, request, pk, att_id):
        att, _ = self._get_att(request, pk, att_id)
        att.delete()
        return Response(status=204)


class ProjectNoteView(APIView):
    """Note personnelle : toujours scopée à request.user, jamais exposée aux autres membres."""
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def _get_project(self, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(self.request, project)
        return project

    def get(self, request, pk):
        project = self._get_project(pk)
        note, _ = Note.objects.get_or_create(project=project, user=request.user)
        return Response(NoteSerializer(note).data)

    def put(self, request, pk):
        project = self._get_project(pk)
        note, _ = Note.objects.get_or_create(project=project, user=request.user)
        note.content = request.data.get('content', '')
        note.save(update_fields=['content', 'updated_at'])
        return Response(NoteSerializer(note).data)


class FolderListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def _get_project(self, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(self.request, project)
        return project

    def get(self, request, pk):
        project = self._get_project(pk)
        folders = project.folders.all()
        return Response(FolderSerializer(folders, many=True).data)

    def post(self, request, pk):
        project = self._get_project(pk)
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'name': 'Ce champ est obligatoire.'}, status=400)
        parent = None
        parent_id = request.data.get('parent_id')
        if parent_id:
            parent = get_object_or_404(Folder, pk=parent_id, project=project)
        folder = Folder.objects.create(
            project=project, name=name, parent=parent, created_by=request.user
        )
        return Response(FolderSerializer(folder).data, status=201)


class FolderDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def delete(self, request, pk, folder_id):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        folder = get_object_or_404(Folder, pk=folder_id, project=project)
        folder.delete()
        return Response(status=204)


class FolderDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, pk, folder_id):
        import zipfile
        from io import BytesIO

        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        folder = get_object_or_404(Folder, pk=folder_id, project=project)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            self._add_folder(zf, folder, folder.name)

        buffer.seek(0)
        safe_name = folder.name.replace(' ', '_').replace('/', '-')
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{safe_name}.zip"'
        return response

    def _add_folder(self, zf, folder, path_prefix):
        for att in folder.attachments.all():
            try:
                zf.write(att.file.path, arcname=f"{path_prefix}/{att.name}")
            except (FileNotFoundError, ValueError):
                pass
        for child in folder.children.all():
            self._add_folder(zf, child, f"{path_prefix}/{child.name}")


class DashboardFrontView(LoginRequiredMixin, ListView):
    template_name = 'projects/dashboard.html'
    context_object_name = 'projects'

    def get_queryset(self):
        user = self.request.user
        settings = ProjectSettings.get()
        if user.is_staff and settings.admin_see_all_projects:
            return Project.objects.select_related('manager').filter(status='active')
        return Project.objects.filter(
            memberships__user=user, status='active'
        ).select_related('manager').distinct()

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from django.db.models import Avg, Count, Q
        from apps.tasks.models import Task

        ctx = super().get_context_data(**kwargs)
        project_ids = [p.id for p in ctx['projects']]
        tasks = Task.objects.filter(project_id__in=project_ids, is_summary=False)
        today = timezone.now().date()
        ctx['total_tasks'] = tasks.count()
        overdue_qs = tasks.filter(
            planned_end__lt=today, percent_complete__lt=100
        ).exclude(status='completed').select_related('project').order_by('planned_end')
        ctx['overdue_tasks'] = overdue_qs.count()
        ctx['overdue_task_list'] = overdue_qs
        progresses = [p.progress for p in ctx['projects']]
        ctx['avg_progress'] = round(sum(progresses) / len(progresses), 1) if progresses else 0
        return ctx
