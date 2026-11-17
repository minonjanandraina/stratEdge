from django.contrib import admin
from .models import Objective, Indicator


class IndicatorInline(admin.TabularInline):
    model = Indicator
    extra = 1
    fields = ['label', 'unit', 'baseline_value', 'target_value', 'current_value',
              'verification_source', 'measurement_frequency', 'measured_at']


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'project', 'responsible', 'status', 'target_date', 'order']
    list_filter = ['level', 'status', 'project']
    search_fields = ['title', 'description']
    raw_id_fields = ['project', 'parent', 'responsible']
    filter_horizontal = ['tasks']
    inlines = [IndicatorInline]
    ordering = ['project', 'order']


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ['label', 'unit', 'objective', 'target_value', 'current_value', 'measured_at']
    list_filter = ['unit', 'objective__project']
    search_fields = ['label', 'objective__title']
