# ats_checker/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect  # ← This import is REQUIRED

def redirect_to_react(request):
    """Redirect root URL to React frontend (Vite dev server)"""
    return HttpResponseRedirect("http://localhost:5173")  # ← Vite port

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('analyzer.urls')),
    
    # 👇 THIS LINE MUST BE HERE (and must be LAST non-media route)
    path('', redirect_to_react),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)