"""
Voice API URL configuration.

Requirements: 9.1-9.7, 13.1
"""

from django.urls import path

from .views import (
    VoiceEnableView,
    VoiceProfileView,
    VoiceApproveSessionView,
    VoiceCallView,
    VoiceCallDetailView,
    VoiceCallListView,
    VoiceCallTranscriptView,
)

app_name = 'voice'

urlpatterns = [
    path('', VoiceProfileView.as_view(), name='profile'),
    path('enable', VoiceEnableView.as_view(), name='enable'),
    path('approve-session', VoiceApproveSessionView.as_view(), name='approve-session'),
    path('call', VoiceCallView.as_view(), name='call'),
    path('calls', VoiceCallListView.as_view(), name='calls'),
    path('calls/<str:call_id>', VoiceCallDetailView.as_view(), name='call-detail'),
    path('calls/<str:call_id>/transcript', VoiceCallTranscriptView.as_view(), name='call-transcript'),
]
