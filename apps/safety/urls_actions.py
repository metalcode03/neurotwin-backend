"""
Actions API URL configuration (for undo functionality).

Requirements: 12.6, 13.1
"""

from django.urls import path

from .views import (
    ReversibleActionsView,
    ActionUndoView,
    ActionApproveView,
    ActionRejectView,
)

app_name = 'actions'

urlpatterns = [
    path('', ReversibleActionsView.as_view(), name='list'),
    path('<str:action_id>/undo', ActionUndoView.as_view(), name='undo'),
    path('<str:action_id>/approve', ActionApproveView.as_view(), name='approve'),
    path('<str:action_id>/reject', ActionRejectView.as_view(), name='reject'),
]
