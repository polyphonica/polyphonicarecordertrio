from django.contrib import admin
from .models import TrioInfo, PlayerBio


@admin.register(TrioInfo)
class TrioInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'updated_at']

    def has_add_permission(self, request):
        # Only allow one TrioInfo instance
        if TrioInfo.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(PlayerBio)
class PlayerBioAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active']
    list_filter = ['is_active']
    list_editable = ['display_order', 'is_active']
    search_fields = ['name', 'bio']
    ordering = ['display_order', 'name']
