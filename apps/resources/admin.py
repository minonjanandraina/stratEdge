from django.contrib import admin
from .models import Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'resource_type', 'max_units']
    list_filter = ['resource_type', 'project']
    search_fields = ['name']
    raw_id_fields = ['project', 'user']
