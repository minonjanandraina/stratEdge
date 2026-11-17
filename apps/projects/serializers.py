from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, ProjectMembership, Holiday, Attachment, Folder, Note
from apps.accounts.serializers import UserSerializer


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'name', 'file_url', 'size', 'uploaded_by_name', 'uploaded_at', 'folder_id']

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return ''
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.username

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent_id', 'created_at']
        read_only_fields = ['created_at']


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'content', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'date', 'name']


class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = ProjectMembership
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['joined_at']


class ProjectListSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    progress = serializers.ReadOnlyField()
    duration_days = serializers.ReadOnlyField()
    tasks_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status', 'color', 'manager',
            'start_date', 'end_date', 'actual_start', 'actual_end',
            'progress', 'duration_days',
            'tasks_count', 'members_count', 'created_at', 'updated_at',
        ]

    def get_tasks_count(self, obj):
        return obj.tasks.filter(is_summary=False).count()

    def get_members_count(self, obj):
        return obj.memberships.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='manager', write_only=True, required=False
    )
    memberships = ProjectMembershipSerializer(many=True, read_only=True)
    holidays = HolidaySerializer(many=True, read_only=True)
    progress = serializers.ReadOnlyField()
    duration_days = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status', 'color',
            'manager', 'manager_id', 'memberships', 'holidays',
            'start_date', 'end_date', 'actual_start', 'actual_end',
            'working_days', 'working_hours_per_day',
            'progress', 'duration_days', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if 'manager' not in validated_data and request:
            validated_data['manager'] = request.user
        project = super().create(validated_data)
        if request:
            ProjectMembership.objects.get_or_create(
                project=project, user=request.user,
                defaults={'role': 'pm'}
            )
        return project
