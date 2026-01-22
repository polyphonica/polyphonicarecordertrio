from django.contrib import admin
from .models import Concert, ConcertTicketOrder


@admin.register(Concert)
class ConcertAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'time', 'venue_name', 'status', 'ticket_source', 'tickets_sold']
    list_filter = ['status', 'ticket_source', 'date']
    search_fields = ['title', 'description', 'venue_name']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-date']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'programme', 'image')
        }),
        ('Date & Time', {
            'fields': ('date', 'time', 'doors_open')
        }),
        ('Venue', {
            'fields': ('venue_name', 'venue_address', 'venue_postcode', 'venue_map_link')
        }),
        ('Tickets', {
            'fields': ('ticket_source', 'external_ticket_url', 'full_price', 'discount_price', 'discount_label', 'capacity', 'tickets_sold')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )


@admin.register(ConcertTicketOrder)
class ConcertTicketOrderAdmin(admin.ModelAdmin):
    list_display = ['name', 'concert', 'ticket_type', 'quantity', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'ticket_type', 'concert']
    search_fields = ['name', 'email']
    ordering = ['-created_at']
    readonly_fields = ['stripe_payment_intent_id', 'stripe_checkout_session_id', 'paid_at', 'created_at']
