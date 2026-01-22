from django.urls import path
from . import views, staff_views

app_name = 'about'

urlpatterns = [
    path('', views.index, name='index'),

    # Staff views
    path('staff/', staff_views.about_edit, name='staff_about_edit'),
    path('staff/musicians/', staff_views.player_list, name='staff_player_list'),
    path('staff/musicians/add/', staff_views.player_create, name='staff_player_create'),
    path('staff/musicians/<int:pk>/edit/', staff_views.player_edit, name='staff_player_edit'),
    path('staff/musicians/<int:pk>/delete/', staff_views.player_delete, name='staff_player_delete'),
]
