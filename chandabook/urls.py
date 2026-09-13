from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render


def offline_view(request):
    return render(request, "festival/offline.html", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("festival.urls")),

    # PWA required files served from root
    path(
        "manifest.json",
        TemplateView.as_view(
            template_name="manifest.json",
            content_type="application/manifest+json",
        ),
        name="manifest",
    ),
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js",
            content_type="application/javascript",
        ),
        name="service_worker",
    ),
    path("offline/", offline_view, name="offline"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
