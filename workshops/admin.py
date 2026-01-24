from django.contrib import admin
from .models import Workshop, WorkshopRegistration, WorkshopMaterial, WorkshopTerms


class WorkshopMaterialInline(admin.TabularInline):
    model = WorkshopMaterial
    extra = 0


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'start_time', 'delivery_method', 'price', 'current_registrations', 'max_participants', 'status']
    list_filter = ['status', 'delivery_method', 'date']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-date']
    inlines = [WorkshopMaterialInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'short_description', 'image')
        }),
        ('Date & Time', {
            'fields': ('date', 'start_time', 'end_time', 'duration_hours'),
            'description': 'Duration is calculated automatically from start and end times.'
        }),
        ('Delivery', {
            'fields': ('delivery_method',)
        }),
        ('Venue (for in-person)', {
            'fields': ('venue_name', 'venue_address', 'venue_postcode', 'venue_map_link'),
            'classes': ('collapse',)
        }),
        ('Online Details', {
            'fields': ('meeting_link', 'meeting_password'),
            'classes': ('collapse',)
        }),
        ('Requirements', {
            'fields': ('prerequisites', 'materials_needed'),
            'classes': ('collapse',)
        }),
        ('Pricing & Capacity', {
            'fields': ('price', 'max_participants', 'current_registrations')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )

    readonly_fields = ['current_registrations', 'duration_hours']


@admin.register(WorkshopRegistration)
class WorkshopRegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'workshop', 'status', 'amount_paid', 'created_at']
    list_filter = ['status', 'workshop']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['stripe_payment_intent_id', 'stripe_checkout_session_id', 'paid_at', 'terms_accepted_at', 'created_at']


@admin.register(WorkshopMaterial)
class WorkshopMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'workshop', 'available_before', 'available_after']
    list_filter = ['workshop', 'available_before', 'available_after']
    search_fields = ['title', 'description']


@admin.register(WorkshopTerms)
class WorkshopTermsAdmin(admin.ModelAdmin):
    list_display = ['version', 'effective_date', 'is_current', 'created_at']
    list_filter = ['is_current']
    ordering = ['-version']
