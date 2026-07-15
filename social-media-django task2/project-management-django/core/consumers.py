import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """One socket per logged-in user; pushes notification events to them."""

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Called when something does group_send({'type': 'notify', ...})
    async def notify(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'link': event.get('link'),
        }))


class ProjectConsumer(AsyncWebsocketConsumer):
    """One socket per open project board; pushes task/member events live."""

    async def connect(self):
        user = self.scope.get('user')
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        if not user or not user.is_authenticated or not await self._is_member(user.id, self.project_id):
            await self.close()
            return

        self.group_name = f'project_{self.project_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _is_member(self, user_id, project_id):
        from .models import ProjectMember
        return ProjectMember.objects.filter(project_id=project_id, user_id=user_id).exists()

    # Called when something does group_send({'type': 'project_event', ...})
    async def project_event(self, event):
        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            'payload': event.get('payload'),
        }))
