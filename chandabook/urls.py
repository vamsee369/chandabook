from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse
import traceback


def offline_view(request):
    return render(request, "festival/offline.html", status=200)


def debug_test(request):
    output = []
    try:
        from festival.models import ChandaCollection, FestivalExpense
        output.append("✅ Models imported OK")
    except Exception as e:
        output.append(f"❌ Model import failed: {e}")
        output.append(traceback.format_exc())
        return HttpResponse("<br>".join(output))

    try:
        list(ChandaCollection.objects.all()[:3])
        output.append("✅ ChandaCollection query OK")
    except Exception as e:
        output.append(f"❌ ChandaCollection query failed: {e}")
        output.append(traceback.format_exc())

    try:
        list(FestivalExpense.objects.all()[:3])
        output.append("✅ FestivalExpense query OK")
    except Exception as e:
        output.append(f"❌ FestivalExpense query failed: {e}")
        output.append(traceback.format_exc())

    try:
        from django.contrib.admin import site
        output.append(f"✅ Admin site OK, registered: {list(site._registry.keys())[:5]}")
    except Exception as e:
        output.append(f"❌ Admin site error: {e}")
        output.append(traceback.format_exc())

    return HttpResponse("<br><br>".join(output))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("festival.urls")),
    path("debug-test/", debug_test),

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
