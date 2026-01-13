"""
Actions API URL configuration (for undo functionality).

Requirements: 12.6, 13.1
"""

from django.urls import path

from .views import ReversibleActionsView, ActionUndoView

app_name = 'actions'

urlpatterns = [
    path('', ReversibleActionsView.as_view(), name='list'),
    path('<str:action_id>/undo', ActionUndoView.as_view(), name='undo'),
]
