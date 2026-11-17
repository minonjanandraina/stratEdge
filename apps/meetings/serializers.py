from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Meeting, MeetingMinute, MeetingDecision


class ParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class MeetingDecisionSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assigned_to',
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = MeetingDecision
        fields = [
            'id', 'description', 'assigned_to_name', 'assigned_to_id',
            'due_date', 'status', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None


class MeetingMinuteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingMinute
        fields = ['id', 'content', 'updated_at']
        read_only_fields = ['updated_at']


class MeetingListSerializer(serializers.ModelSerializer):
    decisions_count = serializers.SerializerMethodField()
    open_decisions_count = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'title', 'date', 'location', 'status',
            'decisions_count', 'open_decisions_count', 'participants_count',
            'created_at',
        ]

    def get_decisions_count(self, obj):
        return obj.decisions.count()

    def get_open_decisions_count(self, obj):
        return obj.decisions.filter(status='open').count()

    def get_participants_count(self, obj):
        return obj.participants.count()


class MeetingSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    participant_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, source='participants',
        write_only=True, required=False,
    )
    decisions = MeetingDecisionSerializer(many=True, read_only=True)
    minutes = MeetingMinuteSerializer(read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'title', 'date', 'location', 'status',
            'participants', 'participant_ids',
            'decisions', 'minutes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
