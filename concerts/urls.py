from django.urls import path
from . import views
from . import staff_views

app_name = 'concerts'

urlpatterns = [
    path('', views.index, name='index'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Staff management
    path('manage/', staff_views.concert_list, name='staff_concert_list'),
    path('manage/create/', staff_views.concert_create, name='staff_concert_create'),
    path('manage/<int:pk>/edit/', staff_views.concert_edit, name='staff_concert_edit'),
    path('manage/<int:pk>/delete/', staff_views.concert_delete, name='staff_concert_delete'),
    path('manage/<int:pk>/orders/', staff_views.concert_orders, name='staff_concert_orders'),

    path('<slug:slug>/', views.detail, name='detail'),
    path('<slug:slug>/tickets/', views.order_tickets, name='order_tickets'),
    path('<slug:slug>/checkout/success/', views.checkout_success, name='checkout_success'),
    path('<slug:slug>/checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
]
