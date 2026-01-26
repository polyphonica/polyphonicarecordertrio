from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Event financials
    path('workshop/<int:pk>/', views.workshop_financials, name='workshop_financials'),
    path('concert/<int:pk>/', views.concert_financials, name='concert_financials'),

    # Reporting
    path('comparison/', views.event_comparison, name='event_comparison'),
    path('export/', views.export_csv, name='export_csv'),
]
