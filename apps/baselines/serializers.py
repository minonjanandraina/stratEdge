from rest_framework import serializers
from .models import Baseline, BaselineTask


class BaselineTaskSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    task_wbs = serializers.CharField(source='task.wbs_code', read_only=True)

    class Meta:
        model = BaselineTask
        fields = [
            'id', 'task', 'task_name', 'task_wbs',
            'planned_start', 'planned_end', 'planned_duration',
            'planned_work', 'percent_complete',
        ]


class BaselineSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    tasks = BaselineTaskSerializer(many=True, read_only=True)
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Baseline
        fields = [
            'id', 'project', 'name', 'created_by', 'created_by_name',
            'created_at', 'notes', 'is_active', 'tasks', 'tasks_count',
        ]
        read_only_fields = ['project', 'created_by', 'created_at']

    def get_tasks_count(self, obj):
        return obj.tasks.count()
