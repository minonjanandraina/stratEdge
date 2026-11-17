import asyncio
import json

from django.http import StreamingHttpResponse, HttpResponse


class AsyncStreamingHttpResponse(StreamingHttpResponse):
    """StreamingHttpResponse dont __aiter__ itère nativement sur un générateur async."""

    async def __aiter__(self):
        async for chunk in self._iterator:
            yield self.make_bytes(chunk)
from asgiref.sync import sync_to_async
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get('unread')
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs[:50]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'detail': 'Toutes les notifications marquées comme lues.'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_read(request, pk):
    notif = Notification.objects.filter(pk=pk, user=request.user).first()
    if notif:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return Response({'detail': 'Notification marquée comme lue.'})


_to_thread = lambda fn: sync_to_async(fn, thread_sensitive=False)


async def notification_stream(request):
    is_authenticated, user_id = await _to_thread(
        lambda: (request.user.is_authenticated, request.user.id)
    )()

    if not is_authenticated:
        return HttpResponse(status=401)

    # Last-Event-ID envoyé automatiquement par le navigateur lors d'une reconnexion
    reconnect_last_id = request.META.get('HTTP_LAST_EVENT_ID')

    async def event_stream():
        if reconnect_last_id:
            # Reconnexion : reprendre depuis le dernier ID reçu, pas de re-init du compteur
            try:
                last_id = int(reconnect_last_id)
            except (ValueError, TypeError):
                last_id = 0
        else:
            # Première connexion : initialiser last_id et envoyer le compte non-lu en une seule requête
            init = await _to_thread(lambda: {
                'last_id': Notification.objects.filter(user_id=user_id)
                           .values_list('id', flat=True).first() or 0,
                'unread_count': Notification.objects.filter(user_id=user_id, is_read=False).count(),
            })()
            last_id = init['last_id']
            yield f"event: init\ndata: {json.dumps({'unread_count': init['unread_count']})}\n\n"

        tick = 0
        try:
            while True:
                await asyncio.sleep(3)
                tick += 1

                new_notifs = await _to_thread(
                    lambda lid=last_id: list(
                        Notification.objects.filter(user_id=user_id, id__gt=lid)
                        .order_by('id')[:20]
                    )
                )()

                for notif in new_notifs:
                    last_id = notif.id
                    payload = {
                        'id': notif.id,
                        'notification_type': notif.notification_type,
                        'title': notif.title,
                        'message': notif.message,
                        'is_read': notif.is_read,
                        'created_at': notif.created_at.isoformat(),
                    }
                    yield f"id: {notif.id}\ndata: {json.dumps(payload)}\n\n"

                if tick % 10 == 0:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass

    response = AsyncStreamingHttpResponse(
        streaming_content=event_stream(),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
