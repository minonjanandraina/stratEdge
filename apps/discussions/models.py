from django.db import models
from django.contrib.auth.models import User

IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


class Message(models.Model):
    TYPE_TEXT = 'text'
    TYPE_FILE = 'file'
    TYPE_CHOICES = [(TYPE_TEXT, 'Texte'), (TYPE_FILE, 'Fichier')]

    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='discussion_messages',
    )
    message_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='discussions/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        label = self.content[:50] if self.message_type == self.TYPE_TEXT else f'[fichier] {self.content}'
        return f'{self.author.username} → {self.department.name}: {label}'

    @property
    def is_image(self):
        if not self.file:
            return False
        return self.file.name.rsplit('.', 1)[-1].lower() in IMAGE_EXTENSIONS

    def to_dict(self):
        full_name = self.author.get_full_name() or self.author.username
        data = {
            'id': self.id,
            'message_type': self.message_type,
            'content': self.content,
            'author_id': self.author_id,
            'author_name': full_name,
            'author_initials': full_name[0].upper(),
            'created_at': self.created_at.isoformat(),
        }
        if self.message_type == self.TYPE_FILE and self.file:
            data['file_url'] = self.file.url
            data['is_image'] = self.is_image
        return data
