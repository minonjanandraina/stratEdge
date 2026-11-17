from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project, Attachment
from apps.projects.permissions import IsProjectMember, IsProjectManager, IsProjectContributor
from apps.projects.serializers import AttachmentSerializer
from .models import Task, TaskDependency, TaskNote
from .serializers import (
    TaskSerializer, TaskListSerializer, GanttTaskSerializer,
    ProgressUpdateSerializer, ReorderSerializer, TaskDependencySerializer,
    TaskNoteSerializer,
)


def get_project(kwargs):
    return get_object_or_404(Project, pk=kwargs['project_id'])


class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        project = get_project(self.kwargs)
        # ?flat=true → toutes les tâches à plat (pour la table WBS)
        if self.request.query_params.get('flat'):
            return Task.objects.filter(
                project=project
            ).select_related('parent').prefetch_related('assignments').order_by('order')
        return Task.objects.filter(
            project=project, parent=None
        ).prefetch_related('subtasks', 'assignments', 'predecessors__predecessor').order_by('order')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TaskListSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        from collections import deque
        from django.db.models import F
        from apps.projects.utils import is_project_locked
        from rest_framework.exceptions import PermissionDenied
        project = get_project(self.kwargs)
        if is_project_locked(project):
            raise PermissionDenied('Ce projet est verrouillé (statut terminé ou annulé).')

        try:
            parent_id = int(self.request.data.get('parent') or 0) or None
        except (TypeError, ValueError):
            parent_id = None

        if parent_id:
            all_tasks = list(Task.objects.filter(project=project).values('id', 'parent_id', 'order'))
            task_map = {t['id']: t for t in all_tasks}
            children_map = {}
            for t in all_tasks:
                if t['parent_id']:
                    children_map.setdefault(t['parent_id'], []).append(t['id'])

            parent_task = task_map.get(parent_id)
            if parent_task:
                max_order = parent_task['order']
                queue = deque([parent_id])
                while queue:
                    cur_id = queue.popleft()
                    cur = task_map.get(cur_id)
                    if cur and cur['order'] > max_order:
                        max_order = cur['order']
                    for child_id in children_map.get(cur_id, []):
                        queue.append(child_id)
                insert_order = max_order + 1
                Task.objects.filter(project=project, order__gte=insert_order).update(order=F('order') + 1)
                order = insert_order
            else:
                last = Task.objects.filter(project=project).order_by('order').last()
                order = (last.order + 1) if last else 0
        else:
            last = Task.objects.filter(project=project).order_by('order').last()
            order = (last.order + 1) if last else 0

        serializer.save(project=project, order=order)


class TaskRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        return Task.objects.filter(
            project_id=self.kwargs['project_id']
        ).prefetch_related('subtasks', 'assignments__resource', 'predecessors__predecessor')

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(), pk=self.kwargs['task_id']
        )

    def _check_lock(self):
        from apps.projects.utils import is_project_locked
        from rest_framework.exceptions import PermissionDenied
        task = self.get_object()
        if is_project_locked(task.project):
            raise PermissionDenied('Ce projet est verrouillé (statut terminé ou annulé).')

    def update(self, request, *args, **kwargs):
        self._check_lock()
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._check_lock()
        return super().destroy(request, *args, **kwargs)


class GanttDataView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_project({'project_id': project_id})
        tasks = Task.objects.filter(project=project).order_by('order')
        deps = TaskDependency.objects.filter(predecessor__project=project)

        task_data = GanttTaskSerializer(tasks, many=True).data
        link_data = [
            {
                'id': d.id,
                'source': d.predecessor_id,
                'target': d.successor_id,
                'type': {'FS': '0', 'SS': '1', 'FF': '2', 'SF': '3'}.get(d.dependency_type, '0'),
                'lag': float(d.lag),
            }
            for d in deps
        ]
        return Response({'data': task_data, 'links': link_data})


class CriticalPathView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id):
        project = get_project({'project_id': project_id})
        tasks = Task.objects.filter(project=project, is_critical=True).order_by('order')
        return Response(TaskListSerializer(tasks, many=True).data)


class ProgressUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    @staticmethod
    def _can_update(user, task):
        from apps.projects.models import ProjectMembership
        from apps.assignments.models import Assignment
        if task.project.manager == user or user.is_staff:
            return True
        if ProjectMembership.objects.filter(project=task.project, user=user, role='pm').exists():
            return True
        return Assignment.objects.filter(task=task, resource__user=user).exists()

    def post(self, request, project_id, task_id):
        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        if not self._can_update(request.user, task):
            return Response(
                {'detail': 'Vous ne pouvez mettre à jour que les tâches qui vous sont assignées.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field, value in data.items():
            setattr(task, field, value)
        if task.percent_complete == 100 and not task.status == 'completed':
            task.status = 'completed'
        task.save()
        return Response(TaskSerializer(task).data)


class ReorderView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def post(self, request, project_id):
        project = get_project({'project_id': project_id})
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task = get_object_or_404(Task, pk=data['task_id'], project=project)
        task.order = data['new_order']
        if 'new_parent' in data:
            if data['new_parent']:
                task.parent = get_object_or_404(Task, pk=data['new_parent'], project=project)
            else:
                task.parent = None
        task.save()
        from .services import recalculate_wbs
        recalculate_wbs(project)
        return Response({'detail': 'Ordre mis à jour.'})


class DependencyListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskDependencySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_queryset(self):
        return TaskDependency.objects.filter(
            predecessor__project_id=self.kwargs['project_id']
        ).select_related('predecessor', 'successor')

    def validate_project_tasks(self, data):
        pid = self.kwargs['project_id']
        if data['predecessor'].project_id != int(pid) or data['successor'].project_id != int(pid):
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Les tâches doivent appartenir au même projet.')

    def perform_create(self, serializer):
        self.validate_project_tasks(serializer.validated_data)
        serializer.save()


class DependencyDestroyView(generics.DestroyAPIView):
    serializer_class = TaskDependencySerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def get_object(self):
        return get_object_or_404(
            TaskDependency,
            pk=self.kwargs['dep_id'],
            predecessor__project_id=self.kwargs['project_id'],
        )


def _propagate_assignment_up(task, resource):
    """Ensure resource is reflected on all ancestor summary tasks."""
    from apps.assignments.models import Assignment
    parent_id = task.parent_id
    while parent_id:
        parent = Task.objects.filter(pk=parent_id).only('id', 'parent_id', 'is_summary').first()
        if not parent or not parent.is_summary:
            break
        Assignment.objects.get_or_create(
            task=parent, resource=resource,
            defaults={'units': 0, 'planned_work': 0},
        )
        parent_id = parent.parent_id


def _cleanup_parent_assignments(task, resource):
    """Remove resource from ancestor summary tasks when no longer needed."""
    from apps.assignments.models import Assignment
    parent_id = task.parent_id
    while parent_id:
        parent = Task.objects.filter(pk=parent_id).only('id', 'parent_id', 'is_summary').first()
        if not parent or not parent.is_summary:
            break
        still_needed = Assignment.objects.filter(
            task__parent_id=parent_id, resource=resource,
        ).exists()
        if still_needed:
            break
        Assignment.objects.filter(task=parent, resource=resource).delete()
        parent_id = parent.parent_id


class TaskAssigneeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsProjectManager()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    @staticmethod
    def _fmt(a):
        u = a.resource.user
        name = u.get_full_name() or u.username if u else a.resource.name
        parts = (name or '?').split()
        initials = ''.join(p[0] for p in parts[:2]).upper() or '?'
        return {'assignment_id': a.id, 'user_id': u.id if u else None,
                'name': name, 'initials': initials, 'resource_id': a.resource_id}

    @staticmethod
    def _descendant_leaf_ids(task):
        from collections import deque
        all_tasks = list(
            Task.objects.filter(project=task.project).values('id', 'parent_id', 'is_summary')
        )
        children_map = {}
        for t in all_tasks:
            children_map.setdefault(t['parent_id'], []).append(t)
        leaf_ids = []
        queue = deque([task.id])
        while queue:
            cur = queue.popleft()
            for child in children_map.get(cur, []):
                if child['is_summary']:
                    queue.append(child['id'])
                else:
                    leaf_ids.append(child['id'])
        return leaf_ids

    def get(self, request, project_id, task_id):
        from apps.assignments.models import Assignment
        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        if task.is_summary:
            leaf_ids = self._descendant_leaf_ids(task)
            if not leaf_ids:
                return Response([])
            seen, result = set(), []
            for a in Assignment.objects.filter(task_id__in=leaf_ids).select_related('resource__user'):
                if a.resource_id not in seen:
                    seen.add(a.resource_id)
                    result.append(self._fmt(a))
            return Response(result)
        return Response([self._fmt(a) for a in task.assignments.select_related('resource__user')])

    def post(self, request, project_id, task_id):
        from django.contrib.auth.models import User as DjangoUser
        from apps.resources.models import Resource
        from apps.assignments.models import Assignment
        from apps.projects.models import ProjectMembership

        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        if task.is_summary:
            return Response(
                {'detail': 'Les tâches récapitulatives reçoivent leurs membres automatiquement depuis leurs sous-tâches.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = task.project
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(DjangoUser, pk=user_id)
        if not ProjectMembership.objects.filter(project=project, user=user).exists():
            return Response({'detail': "Cet utilisateur n'est pas membre du projet."}, status=status.HTTP_400_BAD_REQUEST)

        full_name = user.get_full_name() or user.username
        resource, _ = Resource.objects.get_or_create(
            project=project, user=user,
            defaults={'name': full_name, 'resource_type': 'work'},
        )
        assignment, created = Assignment.objects.get_or_create(
            task=task, resource=resource,
            defaults={
                'units': 100,
                'planned_work': float(task.planned_duration or 1) * 8,
            },
        )
        if not created:
            return Response({'detail': 'Déjà assigné à cette tâche.'}, status=status.HTTP_400_BAD_REQUEST)

        _propagate_assignment_up(task, resource)
        return Response(self._fmt(assignment), status=status.HTTP_201_CREATED)


class TaskAssigneeDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectManager]

    def delete(self, request, project_id, task_id, assignment_id):
        from apps.assignments.models import Assignment
        task = get_object_or_404(Task, pk=task_id, project_id=project_id)
        if task.is_summary:
            return Response(
                {'detail': 'Les assignations des tâches récapitulatives sont gérées automatiquement.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        a = get_object_or_404(Assignment, pk=assignment_id, task=task)
        resource = a.resource
        user = resource.user
        a.delete()
        _cleanup_parent_assignments(task, resource)
        if user:
            from apps.notifications.models import Notification
            Notification.objects.filter(
                user=user, notification_type='task_assigned', related_task=task
            ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskAttachmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]
    parser_classes = [MultiPartParser, FormParser]

    def _get_task(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        self.check_object_permissions(self.request, project)
        return get_object_or_404(Task, pk=self.kwargs['task_id'], project=project)

    def get(self, request, **kwargs):
        task = self._get_task()
        attachments = task.attachments.select_related('uploaded_by')
        return Response(AttachmentSerializer(attachments, many=True, context={'request': request}).data)

    def post(self, request, **kwargs):
        task = self._get_task()
        f = request.FILES.get('file')
        if not f:
            return Response({'file': 'Ce champ est obligatoire.'}, status=400)
        att = Attachment.objects.create(
            task=task, file=f,
            name=request.data.get('name', f.name),
            uploaded_by=request.user, size=f.size,
        )
        return Response(AttachmentSerializer(att, context={'request': request}).data, status=201)


class TaskAttachmentDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def delete(self, request, **kwargs):
        project = get_object_or_404(Project, pk=kwargs['project_id'])
        self.check_object_permissions(request, project)
        att = get_object_or_404(Attachment, pk=kwargs['att_id'], task_id=kwargs['task_id'])
        att.delete()
        return Response(status=204)


class TaskNoteListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        return TaskNote.objects.filter(
            task_id=self.kwargs['task_id'],
            task__project_id=self.kwargs['project_id'],
        ).select_related('created_by').order_by('-created_at')

    def perform_create(self, serializer):
        task = get_object_or_404(
            Task, pk=self.kwargs['task_id'], project_id=self.kwargs['project_id']
        )
        note = serializer.save(task=task, created_by=self.request.user)
        from .tasks import notify_task_note
        notify_task_note.delay(note.id)
