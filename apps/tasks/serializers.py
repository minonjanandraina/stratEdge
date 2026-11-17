from datetime import date
from rest_framework import serializers
from .models import Task, TaskDependency, TaskNote


class TaskDependencySerializer(serializers.ModelSerializer):
    predecessor_name = serializers.CharField(source='predecessor.name', read_only=True)
    successor_name = serializers.CharField(source='successor.name', read_only=True)

    class Meta:
        model = TaskDependency
        fields = ['id', 'predecessor', 'predecessor_name', 'successor', 'successor_name',
                  'dependency_type', 'lag']


class TaskSerializer(serializers.ModelSerializer):
    subtasks = serializers.SerializerMethodField()
    predecessors = TaskDependencySerializer(many=True, read_only=True)
    health_indicator = serializers.ReadOnlyField()
    assignments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'parent', 'name', 'description',
            'wbs_code', 'order', 'level', 'is_milestone', 'is_summary', 'is_recurring',
            'recurrence_rule', 'status', 'planned_start', 'planned_end', 'planned_duration',
            'actual_start', 'actual_end', 'actual_duration', 'percent_complete',
            'constraint_type', 'constraint_date',
            'is_critical', 'critical_override',
            'early_start', 'early_finish', 'late_start', 'late_finish',
            'total_float', 'free_float', 'notes', 'created_at', 'updated_at',
            'subtasks', 'predecessors', 'health_indicator', 'assignments_count',
        ]
        read_only_fields = [
            'wbs_code', 'level', 'is_summary', 'is_critical',
            'early_start', 'early_finish', 'late_start', 'late_finish',
            'total_float', 'free_float', 'created_at', 'updated_at',
        ]

    def get_subtasks(self, obj):
        if obj.subtasks.exists():
            return TaskSerializer(obj.subtasks.order_by('order'), many=True, context=self.context).data
        return []

    def get_assignments_count(self, obj):
        return obj.assignments.count()

    def validate(self, attrs):
        start = attrs.get('planned_start', getattr(self.instance, 'planned_start', None))
        end = attrs.get('planned_end', getattr(self.instance, 'planned_end', None))
        if start and end and end < start:
            raise serializers.ValidationError({'planned_end': 'La date de fin doit être après la date de début.'})

        is_summary = self.instance.is_summary if self.instance else False
        if is_summary and ('status' in attrs or 'percent_complete' in attrs):
            raise serializers.ValidationError(
                'Le statut et l\'avancement d\'une tâche parente sont calculés automatiquement depuis ses sous-tâches.'
            )

        is_milestone = attrs.get('is_milestone', getattr(self.instance, 'is_milestone', False))
        if is_milestone:
            if 'status' in attrs and attrs['status'] not in ('not_started', 'completed', 'cancelled'):
                raise serializers.ValidationError(
                    {'status': 'Un jalon ne peut être qu\'en attente, terminé ou annulé.'}
                )
            if 'percent_complete' in attrs:
                pct = int(attrs['percent_complete'])
                if pct not in (0, 100):
                    raise serializers.ValidationError(
                        {'percent_complete': 'L\'avancement d\'un jalon est 0 % ou 100 % uniquement.'}
                    )

        # Auto-sync status ↔ percent_complete when only one is provided or they contradict
        pct = attrs.get('percent_complete', getattr(self.instance, 'percent_complete', None))
        stat = attrs.get('status', getattr(self.instance, 'status', None))
        if pct is not None and stat is not None and not is_milestone:
            pct_int = int(pct)
            if pct_int == 100 and stat not in ('completed', 'cancelled', 'on_hold'):
                attrs['status'] = 'completed'
            elif 0 < pct_int < 100 and stat == 'completed':
                attrs['status'] = 'in_progress'
            elif pct_int == 0 and stat in ('completed', 'in_progress'):
                attrs['status'] = 'not_started'

        return attrs


class TaskListSerializer(serializers.ModelSerializer):
    health_indicator = serializers.ReadOnlyField()
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    assignments_count = serializers.SerializerMethodField()
    assignee_user_ids = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'parent', 'parent_name', 'name', 'description', 'notes',
            'wbs_code', 'order', 'level',
            'is_milestone', 'is_summary', 'is_critical', 'critical_override', 'status',
            'planned_start', 'planned_end', 'planned_duration',
            'early_start', 'early_finish',
            'actual_start', 'actual_end', 'percent_complete',
            'constraint_type', 'total_float', 'free_float',
            'health_indicator', 'assignments_count', 'assignee_user_ids',
        ]

    def get_assignments_count(self, obj):
        return obj.assignments.count()

    def get_assignee_user_ids(self, obj):
        return list(obj.assignments.filter(
            resource__user__isnull=False
        ).values_list('resource__user_id', flat=True))


class GanttTaskSerializer(serializers.ModelSerializer):
    """Format compatible dhtmlxGantt."""
    start_date = serializers.DateField(source='planned_start')
    end_date = serializers.DateField(source='planned_end')
    text = serializers.CharField(source='name')
    progress = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'text', 'start_date', 'end_date', 'progress',
            'parent', 'is_milestone', 'is_summary', 'is_critical', 'color',
        ]

    def get_progress(self, obj):
        return float(obj.percent_complete) / 100

    def get_color(self, obj):
        if obj.is_critical:
            return '#e74c3c'
        if obj.is_milestone:
            return '#9b59b6'
        if obj.is_summary:
            return '#2980b9'
        return '#27ae60'

    def get_parent(self, obj):
        return obj.parent_id or 0


class ProgressUpdateSerializer(serializers.Serializer):
    percent_complete = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    actual_start = serializers.DateField(required=False, allow_null=True)
    actual_end = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class ReorderSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    new_order = serializers.IntegerField(min_value=0)
    new_parent = serializers.IntegerField(required=False, allow_null=True)


class TaskNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    created_by_initials = serializers.SerializerMethodField()

    class Meta:
        model = TaskNote
        fields = ['id', 'content', 'created_by', 'created_by_name', 'created_by_initials', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_created_by_initials(self, obj):
        name = obj.created_by.get_full_name() or obj.created_by.username
        parts = name.split()
        return ''.join(p[0] for p in parts[:2]).upper() or '?'
