from django.contrib import admin
from django.urls import path, include
from .initcmds import init_db
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gestione.urls')),
]

init_db()
# erase_db()

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )