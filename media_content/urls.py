from django.urls import path
from . import views
from . import staff_views

app_name = 'media_content'

urlpatterns = [
    path('', views.index, name='index'),

    # Staff media management
    path('manage/', staff_views.media_list, name='staff_media_list'),
    path('manage/create/', staff_views.media_create, name='staff_media_create'),
    path('manage/<int:pk>/edit/', staff_views.media_edit, name='staff_media_edit'),
    path('manage/<int:pk>/delete/', staff_views.media_delete, name='staff_media_delete'),
]
