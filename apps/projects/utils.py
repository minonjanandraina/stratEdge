from .models import ProjectSettings

LOCKED_STATUSES = ('completed', 'cancelled')


def is_project_locked(project):
    if project.status not in LOCKED_STATUSES:
        return False
    return ProjectSettings.get().lock_on_completion


def set_project_manager(project, user):
    """Un seul chef de projet possible : promeut `user` et rétrograde l'ancien pm."""
    from .models import ProjectMembership

    ProjectMembership.objects.filter(
        project=project, role='pm'
    ).exclude(user=user).update(role='member')

    if project.manager_id != user.id:
        project.manager = user
        project.save(update_fields=['manager'])

        from apps.notifications.utils import notify
        notify(
            user=user,
            notif_type='pm_assigned',
            title=f'Vous avez été nommé(e) chef de projet : {project.name}',
            message=f'Vous êtes désormais chef de projet du projet "{project.name}".',
            project=project,
            send_email=True,
        )


def clear_project_manager(project, user):
    """Efface le chef de projet si `user` (rétrogradé ou retiré) l'occupait."""
    if project.manager_id == user.id:
        project.manager = None
        project.save(update_fields=['manager'])
