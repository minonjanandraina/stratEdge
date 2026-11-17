from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import ProjectMembership


def get_project_from_view(view):
    """Extract project from view kwargs (project_id or pk)."""
    from .models import Project
    pk = view.kwargs.get('project_id') or view.kwargs.get('pk')
    if pk:
        try:
            return Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return None
    return None


class IsProjectMember(BasePermission):
    message = "Vous n'êtes pas membre de ce projet."

    def has_permission(self, request, view):
        project = get_project_from_view(view)
        if not project:
            return True
        return ProjectMembership.objects.filter(
            project=project, user=request.user
        ).exists() or project.manager == request.user or request.user.is_staff

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, 'project', obj)
        return ProjectMembership.objects.filter(
            project=project, user=request.user
        ).exists() or project.manager == request.user or request.user.is_staff


class IsProjectManager(BasePermission):
    message = "Vous devez être membre du projet pour effectuer cette action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        project = get_project_from_view(view)
        if not project:
            return True
        return (
            ProjectMembership.objects.filter(project=project, user=request.user).exists()
            or project.manager == request.user
            or request.user.is_staff
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        project = getattr(obj, 'project', obj)
        return (
            ProjectMembership.objects.filter(project=project, user=request.user).exists()
            or project.manager == request.user
            or request.user.is_staff
        )


class IsProjectContributor(BasePermission):
    """All members can read and write."""
    message = "Vous devez être membre du projet pour effectuer cette action."

    def has_permission(self, request, view):
        project = get_project_from_view(view)
        if not project:
            return True
        if project.manager == request.user or request.user.is_staff:
            return True
        return ProjectMembership.objects.filter(project=project, user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, 'project', obj)
        if project.manager == request.user or request.user.is_staff:
            return True
        return ProjectMembership.objects.filter(project=project, user=request.user).exists()


class IsProjectAdmin(BasePermission):
    message = "Seul l'administrateur du projet peut effectuer cette action."

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, 'project', obj)
        return project.manager == request.user or request.user.is_staff
