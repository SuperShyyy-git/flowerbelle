# flowerbelle_project/urls.py (or whatever your main folder is named)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Redirect root to API auth
    path('', lambda request: redirect('api/auth/')),
    
    path('admin/', admin.site.urls),
    
    # App Includes
    path('api/auth/', include('accounts.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/pos/', include('pos.urls')),
    path('api/forecasting/', include('forecasting.urls')),
    
    # ✅ THIS LINKS TO THE FILE WE JUST FIXED
    path('api/reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)