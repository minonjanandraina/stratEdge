from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Objective, Indicator


class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = [
            'id', 'label', 'unit',
            'baseline_value', 'target_value', 'current_value',
            'verification_source', 'measurement_frequency', 'measured_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ObjectiveListSerializer(serializers.ModelSerializer):
    progress = serializers.ReadOnlyField()
    cascade_progress = serializers.ReadOnlyField()
    responsible_name = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Objective
        fields = [
            'id', 'parent', 'level', 'title', 'description',
            'responsible', 'responsible_name', 'target_date', 'status', 'order',
            'assumptions', 'progress', 'cascade_progress',
            'children_count', 'tasks_count',
            'created_at', 'updated_at',
        ]

    def get_responsible_name(self, obj):
        if not obj.responsible:
            return None
        return obj.responsible.get_full_name() or obj.responsible.username

    def get_children_count(self, obj):
        return obj.children.count()

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class ObjectiveDetailSerializer(serializers.ModelSerializer):
    progress = serializers.ReadOnlyField()
    cascade_progress = serializers.ReadOnlyField()
    responsible_name = serializers.SerializerMethodField()
    indicators = IndicatorSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    task_ids = serializers.PrimaryKeyRelatedField(
        source='tasks', many=True, read_only=True
    )

    class Meta:
        model = Objective
        fields = [
            'id', 'project', 'parent', 'level', 'title', 'description',
            'responsible', 'responsible_name', 'target_date', 'status', 'order',
            'assumptions', 'tasks', 'task_ids',
            'progress', 'cascade_progress',
            'indicators', 'children',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['project', 'created_at', 'updated_at']
        extra_kwargs = {
            'tasks': {'write_only': True, 'required': False},
        }

    def get_responsible_name(self, obj):
        if not obj.responsible:
            return None
        return obj.responsible.get_full_name() or obj.responsible.username

    def get_children(self, obj):
        children = obj.children.order_by('order')
        return ObjectiveListSerializer(children, many=True, context=self.context).data

    def validate_parent(self, value):
        if value and value.project_id != self.context['project'].id:
            raise serializers.ValidationError(
                "Le parent doit appartenir au même projet."
            )
        return value

    def validate(self, attrs):
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        level = attrs.get('level', getattr(self.instance, 'level', None))

        if parent and level:
            order = {'impact': 0, 'outcome': 1, 'output': 2}
            if order.get(level, 0) <= order.get(parent.level, 0):
                raise serializers.ValidationError({
                    'level': (
                        f"Un objectif de niveau « {level} » ne peut pas être "
                        f"enfant d'un objectif de niveau « {parent.level} ». "
                        "La hiérarchie doit être impact → outcome → output."
                    )
                })
        return attrs


class ObjectiveTreeSerializer(serializers.ModelSerializer):
    """Full recursive tree — used for the LogFrame tree view."""
    progress = serializers.ReadOnlyField()
    cascade_progress = serializers.ReadOnlyField()
    indicators = IndicatorSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    responsible_name = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    task_ids = serializers.SerializerMethodField()

    class Meta:
        model = Objective
        fields = [
            'id', 'parent', 'level', 'title', 'description',
            'responsible', 'responsible_name', 'target_date', 'status', 'order',
            'assumptions', 'progress', 'cascade_progress',
            'tasks_count', 'task_ids', 'indicators', 'children',
        ]

    def get_children(self, obj):
        children = obj.children.prefetch_related('children', 'indicators', 'tasks').order_by('order')
        return ObjectiveTreeSerializer(children, many=True, context=self.context).data

    def get_responsible_name(self, obj):
        if not obj.responsible:
            return None
        return obj.responsible.get_full_name() or obj.responsible.username

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_task_ids(self, obj):
        return list(obj.tasks.values_list('id', flat=True))
