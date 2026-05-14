# analyzer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Upload endpoint
    path('upload/', views.upload_resume, name='upload_resume'),
    
    # List candidates (legacy)
    path('candidates/', views.list_candidates, name='list_candidates'),
    
    # ML analysis endpoint
    path('ml-analyze/', views.ml_analyze, name='ml_analyze'),
    
    # Dashboard endpoints
    path('dashboard/', views.dashboard_data, name='dashboard_data'),           # All candidates
    path('dashboard/latest/', views.dashboard_latest, name='dashboard_latest'), # Latest batch only
    path('dashboard/history/', views.dashboard_history, name='dashboard_history'), # ALL history (paginated)
    

]