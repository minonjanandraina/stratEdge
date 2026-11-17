from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from .models import Message

ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'csv', 'zip',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class DiscussionRoomView(LoginRequiredMixin, TemplateView):
    template_name = 'discussions/room.html'

    def dispatch(self, request, *args, **kwargs):
        dept = getattr(getattr(request.user, 'profile', None), 'department', None)
        if not dept:
            messages.error(request, "Vous n'avez pas de département assigné. Contactez un administrateur.")
            return redirect('project-list-front')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dept = self.request.user.profile.department
        initial_messages = (
            Message.objects
            .filter(department=dept)
            .select_related('author')
            .order_by('created_at')
        )
        members = dept.members.select_related('user').all()
        ctx['department'] = dept
        ctx['initial_messages'] = initial_messages
        ctx['members'] = members
        ctx['current_user_id'] = self.request.user.id
        return ctx


class FileUploadView(LoginRequiredMixin, View):
    def post(self, request):
        dept = getattr(getattr(request.user, 'profile', None), 'department', None)
        if not dept:
            return JsonResponse({'ok': False, 'error': 'Pas de département assigné.'}, status=403)

        uploaded = request.FILES.get('file')
        if not uploaded:
            return JsonResponse({'ok': False, 'error': 'Aucun fichier reçu.'}, status=400)

        if uploaded.size > MAX_FILE_SIZE:
            return JsonResponse({'ok': False, 'error': 'Fichier trop volumineux (max 10 Mo).'}, status=400)

        ext = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext not in ALLOWED_EXTENSIONS:
            return JsonResponse({'ok': False, 'error': 'Type de fichier non autorisé.'}, status=400)

        msg = Message.objects.create(
            department=dept,
            author=request.user,
            message_type=Message.TYPE_FILE,
            content=uploaded.name,
            file=uploaded,
        )

        async_to_sync(get_channel_layer().group_send)(
            f'discussion_dept_{dept.id}',
            {'type': 'chat_message', 'data': msg.to_dict()},
        )

        return JsonResponse({'ok': True})
