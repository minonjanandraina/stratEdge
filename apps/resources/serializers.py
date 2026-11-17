from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Resource
from apps.accounts.serializers import UserSerializer


class ResourceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True, required=False, allow_null=True
    )
    assignments_count = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'project', 'user', 'user_id', 'name', 'resource_type',
            'max_units', 'availability_start', 'availability_end',
            'material_unit', 'working_days', 'notes', 'assignments_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['project', 'created_at', 'updated_at']

    def get_assignments_count(self, obj):
        return obj.assignments.count()


class ResourceUtilizationSerializer(serializers.Serializer):
    resource_id = serializers.IntegerField()
    resource_name = serializers.CharField()
    daily_utilization = serializers.DictField()
    is_overallocated = serializers.BooleanField()
    max_utilization = serializers.FloatField()
    avg_utilization = serializers.FloatField()
