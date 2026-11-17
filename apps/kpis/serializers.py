from rest_framework import serializers
from .models import ProjectKPI


class ProjectKPISerializer(serializers.ModelSerializer):
    spi_status = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = ProjectKPI
        fields = [
            'id', 'project', 'baseline', 'calculated_at', 'status_date',
            'spi', 'sv',
            'total_tasks', 'completed_tasks', 'overdue_tasks',
            'milestones_reached', 'milestones_total', 'critical_tasks_count',
            'overall_percent_complete',
            'total_resources', 'overallocated_resources', 'resource_utilization_avg',
            'schedule_health', 'resource_health',
            'spi_status', 'completion_rate',
        ]

    def get_spi_status(self, obj):
        if obj.spi >= 1:
            return 'good'
        if obj.spi >= 0.85:
            return 'warning'
        return 'critical'

    def get_completion_rate(self, obj):
        if obj.total_tasks > 0:
            return round((obj.completed_tasks / obj.total_tasks) * 100, 2)
        return 0
