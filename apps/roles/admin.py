"""Django Admin configuration for the roles app."""

from django.contrib import admin

from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system", "is_active", "created_at")
    list_filter = ("is_active", "is_system")
    search_fields = ("name", "code")
    ordering = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
