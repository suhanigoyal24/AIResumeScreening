from django.urls import path
from . import views
from . import auth_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth
    path('auth/register/', auth_views.register, name='register'),
    path('auth/login/', auth_views.login, name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', auth_views.profile, name='profile'),

    # Resume screening
    path('upload/', views.upload_resume, name='upload_resume'),
    path('candidates/', views.list_candidates, name='list_candidates'),
    path('ml-analyze/', views.ml_analyze, name='ml_analyze'),

    # Dashboard
    path('dashboard/', views.dashboard_data, name='dashboard_data'),
    path('dashboard/latest/', views.dashboard_latest, name='dashboard_latest'),
    path('dashboard/history/', views.dashboard_history, name='dashboard_history'),
    path('dashboard/session/<str:session_id>/', views.dashboard_by_session, name='dashboard_by_session'),
]