from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.projects.permissions import IsProjectMember, IsProjectContributor
from .models import Meeting, MeetingMinute, MeetingDecision
from .serializers import (
    MeetingSerializer, MeetingListSerializer,
    MeetingMinuteSerializer, MeetingDecisionSerializer,
)


def _get_project(kwargs):
    return get_object_or_404(Project, pk=kwargs['project_id'])


def _get_meeting(kwargs):
    return get_object_or_404(Meeting, pk=kwargs['meeting_id'], project_id=kwargs['project_id'])


class MeetingListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return MeetingListSerializer
        return MeetingSerializer

    def get_queryset(self):
        project = _get_project(self.kwargs)
        return Meeting.objects.filter(project=project).prefetch_related('decisions', 'participants')

    def perform_create(self, serializer):
        project = _get_project(self.kwargs)
        meeting = serializer.save(project=project, created_by=self.request.user)

        # Notification #9 — Réunion planifiée → participants (interne uniquement à la création)
        from apps.notifications.models import Notification
        for user in meeting.participants.all():
            Notification.objects.get_or_create(
                user=user,
                notification_type='meeting_reminder',
                related_project=project,
                title=f'Réunion planifiée : {meeting.title}',
                defaults={
                    'message': (
                        f'Vous êtes invité(e) à la réunion "{meeting.title}" '
                        f'le {meeting.date.strftime("%d/%m/%Y à %H:%M")}.'
                        + (f' Lieu : {meeting.location}.' if meeting.location else '')
                    )
                },
            )


class MeetingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MeetingSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [permissions.IsAuthenticated(), IsProjectContributor()]
        return [permissions.IsAuthenticated(), IsProjectMember()]

    def get_object(self):
        return _get_meeting(self.kwargs)


class MeetingMinuteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get(self, request, project_id, meeting_id):
        meeting = _get_meeting({'project_id': project_id, 'meeting_id': meeting_id})
        minute, _ = MeetingMinute.objects.get_or_create(meeting=meeting)
        return Response(MeetingMinuteSerializer(minute).data)

    def put(self, request, project_id, meeting_id):
        meeting = _get_meeting({'project_id': project_id, 'meeting_id': meeting_id})
        minute, _ = MeetingMinute.objects.get_or_create(
            meeting=meeting, defaults={'written_by': request.user}
        )
        serializer = MeetingMinuteSerializer(minute, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(written_by=request.user)
        return Response(serializer.data)


class MeetingDecisionListCreateView(generics.ListCreateAPIView):
    serializer_class = MeetingDecisionSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        meeting = _get_meeting(self.kwargs)
        return MeetingDecision.objects.filter(meeting=meeting).select_related('assigned_to')

    def perform_create(self, serializer):
        meeting = _get_meeting(self.kwargs)
        serializer.save(meeting=meeting)


class MeetingDecisionUpdateDestroyView(generics.UpdateAPIView, generics.DestroyAPIView):
    serializer_class = MeetingDecisionSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectContributor]

    def get_object(self):
        return get_object_or_404(
            MeetingDecision,
            pk=self.kwargs['decision_id'],
            meeting_id=self.kwargs['meeting_id'],
            meeting__project_id=self.kwargs['project_id'],
        )
