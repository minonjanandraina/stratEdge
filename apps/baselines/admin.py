from django.contrib import admin
from .models import Baseline, BaselineTask


class BaselineTaskInline(admin.TabularInline):
    model = BaselineTask
    extra = 0
    readonly_fields = ['task', 'planned_start', 'planned_end', 'planned_duration',
                       'planned_work', 'percent_complete']
    can_delete = False


@admin.register(Baseline)
class BaselineAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'project']
    readonly_fields = ['created_at']
    inlines = [BaselineTaskInline]
