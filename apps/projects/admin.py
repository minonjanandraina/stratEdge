from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import Project, ProjectMembership, Holiday, ProjectSettings, Note


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1
    autocomplete_fields = ['user']


class HolidayInline(admin.TabularInline):
    model = Holiday
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'manager', 'start_date', 'end_date', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'description']
    autocomplete_fields = ['manager']
    inlines = [ProjectMembershipInline, HolidayInline]
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'updated_at']
    list_filter = ['project']
    search_fields = ['user__username', 'user__email', 'project__name', 'content']
    autocomplete_fields = ['project', 'user']
    readonly_fields = ['updated_at']


@admin.register(ProjectSettings)
class ProjectSettingsAdmin(admin.ModelAdmin):
    fields = ['lock_on_completion', 'admin_see_all_projects']

    def has_add_permission(self, request):
        return not ProjectSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ProjectSettings.get()
        return redirect(reverse('admin:projects_projectsettings_change', args=[obj.pk]))
