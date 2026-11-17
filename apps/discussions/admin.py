from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'department', 'author', 'short_content', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['author__username', 'author__first_name', 'author__last_name', 'content']
    readonly_fields = ['department', 'author', 'content', 'created_at']
    ordering = ['-created_at']

    def short_content(self, obj):
        return obj.content[:80] + '…' if len(obj.content) > 80 else obj.content
    short_content.short_description = 'Message'
