"""Root URL configuration for CrimeGPT.

Day 1 only wires up the Django admin and a health check. DRF routes are added
on Day 2.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health(_request):
    return JsonResponse({"status": "ok", "service": "crimegpt"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
