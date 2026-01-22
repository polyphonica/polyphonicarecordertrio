from django.urls import path
from . import views
from . import staff_views

app_name = 'workshops'

urlpatterns = [
    path('', views.index, name='index'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('registration/<int:registration_id>/cancel/', views.cancel_registration, name='cancel_registration'),

    # Staff management
    path('manage/', staff_views.workshop_list, name='staff_workshop_list'),
    path('manage/create/', staff_views.workshop_create, name='staff_workshop_create'),
    path('manage/<int:pk>/edit/', staff_views.workshop_edit, name='staff_workshop_edit'),
    path('manage/<int:pk>/delete/', staff_views.workshop_delete, name='staff_workshop_delete'),
    path('manage/<int:pk>/attendees/', staff_views.workshop_attendees, name='staff_workshop_attendees'),
    path('manage/<int:pk>/attendees/pdf/', staff_views.workshop_attendees_pdf, name='staff_workshop_attendees_pdf'),

    path('<slug:slug>/', views.detail, name='detail'),
    path('<slug:slug>/register/', views.register, name='register'),
    path('<slug:slug>/checkout/success/', views.checkout_success, name='checkout_success'),
    path('<slug:slug>/checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
]
