from rest_framework import serializers
from .models import Assignment, TimeEntry
from apps.resources.models import Resource
from apps.resources.serializers import ResourceSerializer


class TimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ['id', 'assignment', 'date', 'hours', 'is_overtime', 'notes', 'created_at']
        read_only_fields = ['created_at']


class AssignmentSerializer(serializers.ModelSerializer):
    resource = ResourceSerializer(read_only=True)
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(),
        source='resource', write_only=True
    )
    task_name = serializers.CharField(source='task.name', read_only=True)
    time_entries = TimeEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'task', 'task_name', 'resource', 'resource_id',
            'units', 'planned_work', 'actual_work', 'remaining_work',
            'start_date', 'end_date', 'notes', 'created_at', 'time_entries',
        ]
        read_only_fields = ['created_at']
