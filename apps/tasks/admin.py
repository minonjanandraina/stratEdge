from django.contrib import admin
from .models import Task, TaskDependency, TaskNote


class TaskDependencyInline(admin.TabularInline):
    model = TaskDependency
    fk_name = 'predecessor'
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['wbs_code', 'name', 'project', 'status', 'percent_complete',
                    'planned_start', 'planned_end', 'is_critical', 'is_milestone']
    list_filter = ['status', 'is_critical', 'is_milestone', 'project']
    search_fields = ['name', 'wbs_code']
    readonly_fields = ['wbs_code', 'level', 'is_summary', 'early_start', 'early_finish',
                       'late_start', 'late_finish', 'total_float', 'free_float']
    inlines = [TaskDependencyInline]
    raw_id_fields = ['project', 'parent']


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ['predecessor', 'successor', 'dependency_type', 'lag']
    raw_id_fields = ['predecessor', 'successor']


@admin.register(TaskNote)
class TaskNoteAdmin(admin.ModelAdmin):
    list_display = ['task', 'created_by', 'created_at', 'content_preview']
    list_filter = ['task__project', 'created_by']
    search_fields = ['content', 'task__name', 'created_by__username']
    readonly_fields = ['created_at']
    raw_id_fields = ['task', 'created_by']

    def content_preview(self, obj):
        return obj.content[:80] + '…' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Contenu'
