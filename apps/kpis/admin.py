from django.contrib import admin
from .models import ProjectKPI


@admin.register(ProjectKPI)
class ProjectKPIAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'status_date', 'spi', 'sv',
        'schedule_health', 'calculated_at',
    ]
    list_filter = ['schedule_health', 'project']
    readonly_fields = [f.name for f in ProjectKPI._meta.fields]
    date_hierarchy = 'status_date'
