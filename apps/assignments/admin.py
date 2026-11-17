from django.contrib import admin
from .models import Assignment, TimeEntry


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'resource', 'units', 'planned_work', 'actual_work']
    raw_id_fields = ['task', 'resource']
    inlines = [TimeEntryInline]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'date', 'hours', 'is_overtime']
    list_filter = ['date', 'is_overtime']
    raw_id_fields = ['assignment']
