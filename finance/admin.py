from django.contrib import admin
from .models import StripeTransaction, Expense


@admin.register(StripeTransaction)
class StripeTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'payment_intent_id_short',
        'transaction_type',
        'gross_pounds',
        'fee_pounds',
        'net_pounds',
        'transaction_date',
        'synced_at',
    ]
    list_filter = ['transaction_type', 'transaction_date']
    search_fields = ['payment_intent_id', 'charge_id', 'balance_transaction_id']
    readonly_fields = [
        'payment_intent_id', 'charge_id', 'balance_transaction_id',
        'gross_amount', 'stripe_fee', 'net_amount',
        'transaction_date', 'synced_at', 'updated_at',
        'workshop_registration', 'concert_order',
    ]
    date_hierarchy = 'transaction_date'

    def payment_intent_id_short(self, obj):
        return f"{obj.payment_intent_id[:20]}..."
    payment_intent_id_short.short_description = 'Payment Intent'

    def has_add_permission(self, request):
        return False  # Transactions are created by sync command only

    def has_change_permission(self, request, obj=None):
        return False  # Read-only


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'description',
        'category',
        'amount',
        'expense_date',
        'event_link',
        'created_by',
    ]
    list_filter = ['category', 'expense_date', 'workshop', 'concert']
    search_fields = ['description', 'notes']
    date_hierarchy = 'expense_date'
    readonly_fields = ['created_by', 'created_at', 'updated_at']

    fieldsets = [
        (None, {
            'fields': ['category', 'description', 'notes', 'amount', 'expense_date']
        }),
        ('Link to Event', {
            'fields': ['workshop', 'concert'],
            'description': 'Optionally link this expense to a specific workshop or concert.'
        }),
        ('Receipt', {
            'fields': ['receipt']
        }),
        ('Audit', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def event_link(self, obj):
        if obj.workshop:
            return f"Workshop: {obj.workshop.title}"
        elif obj.concert:
            return f"Concert: {obj.concert.title}"
        return "-"
    event_link.short_description = 'Linked Event'

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
