from django.contrib import admin
from .models import Composer, Piece, Programme, ProgrammeItem


@admin.register(Composer)
class ComposerAdmin(admin.ModelAdmin):
    list_display = ['name', 'birth_year', 'death_year', 'nationality']
    search_fields = ['name', 'nationality']
    list_filter = ['nationality']


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ['title', 'composer', 'duration', 'catalogue_number']
    search_fields = ['title', 'composer__name', 'catalogue_number']
    list_filter = ['composer']
    autocomplete_fields = ['composer']


class ProgrammeItemInline(admin.TabularInline):
    model = ProgrammeItem
    extra = 0
    autocomplete_fields = ['piece']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'piece_count', 'total_duration_display', 'updated_at']
    search_fields = ['title']
    list_filter = ['status']
    inlines = [ProgrammeItemInline]
