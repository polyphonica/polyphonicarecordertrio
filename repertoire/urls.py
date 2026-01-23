from django.urls import path
from . import views

app_name = 'repertoire'

urlpatterns = [
    # Composers
    path('composers/', views.composer_list, name='composer_list'),
    path('composers/add/', views.composer_add, name='composer_add'),
    path('composers/<int:pk>/edit/', views.composer_edit, name='composer_edit'),
    path('composers/<int:pk>/delete/', views.composer_delete, name='composer_delete'),

    # Pieces
    path('pieces/', views.piece_list, name='piece_list'),
    path('pieces/add/', views.piece_add, name='piece_add'),
    path('pieces/<int:pk>/edit/', views.piece_edit, name='piece_edit'),
    path('pieces/<int:pk>/delete/', views.piece_delete, name='piece_delete'),

    # Programmes
    path('programmes/', views.programme_list, name='programme_list'),
    path('programmes/add/', views.programme_add, name='programme_add'),
    path('programmes/<int:pk>/', views.programme_detail, name='programme_detail'),
    path('programmes/<int:pk>/edit/', views.programme_edit, name='programme_edit'),
    path('programmes/<int:pk>/delete/', views.programme_delete, name='programme_delete'),

    # Programme builder AJAX endpoints
    path('programmes/<int:pk>/add-item/', views.programme_add_item, name='programme_add_item'),
    path('programmes/<int:pk>/reorder/', views.programme_reorder, name='programme_reorder'),
    path('programme-items/<int:pk>/edit/', views.programme_item_edit, name='programme_item_edit'),
    path('programme-items/<int:pk>/delete/', views.programme_item_delete, name='programme_item_delete'),

    # PDF exports
    path('programmes/<int:pk>/pdf/performer/', views.programme_pdf_performer, name='programme_pdf_performer'),
    path('programmes/<int:pk>/pdf/public/', views.programme_pdf_public, name='programme_pdf_public'),

    # API for piece search
    path('api/pieces/search/', views.piece_search_api, name='piece_search_api'),
]
