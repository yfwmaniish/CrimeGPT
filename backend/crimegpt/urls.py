"""Root URL configuration for CrimeGPT.

Day 1 only wires up the Django admin and a health check. DRF routes are added
on Day 2.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import CaseViewSet, LoginView, MeView


def health(_request):
    return JsonResponse({"status": "ok", "service": "crimegpt"})


router = DefaultRouter()
router.register(r"cases", CaseViewSet, basename="case")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
