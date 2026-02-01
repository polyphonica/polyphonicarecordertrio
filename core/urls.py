from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('accessibility/', views.accessibility, name='accessibility'),
    path('manage/', views.staff_dashboard, name='staff_dashboard'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
