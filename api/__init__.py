# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('analyze-video', views.analyze_video, name='analyze-video'),
    path('analyze-status', views.analyze_status, name='analyze-status'),
    path('analyze-result', views.analyze_result, name='analyze-result'),
]
