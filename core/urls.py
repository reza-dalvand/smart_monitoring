from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('face/', include('face.urls', namespace='face')),  
    path('national/', include('national.urls', namespace='national')),
    path('province/', include('province.urls', namespace='province')),
    path('district/', include('district.urls', namespace='district')),
    path('school/', include('school.urls', namespace='school')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)