import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class DiscussionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return

        dept_id = await self._get_dept_id(user)
        if not dept_id:
            await self.close()
            return

        self.dept_id = dept_id
        self.group_name = f'discussion_dept_{dept_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            return

        content = data.get('content', '').strip()
        if not content or len(content) > 4000:
            return

        user = self.scope['user']
        msg_data = await self._save_message(user, self.dept_id, content)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'data': msg_data},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def _get_dept_id(self, user):
        try:
            return user.profile.department_id
        except Exception:
            return None

    @database_sync_to_async
    def _save_message(self, user, dept_id, content):
        from .models import Message
        from apps.accounts.models import Department
        dept = Department.objects.get(id=dept_id)
        msg = Message.objects.create(department=dept, author=user, content=content)
        return msg.to_dict()
