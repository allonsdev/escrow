from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "Escrow Payment System Admin"
admin.site.site_title = "Escrow Payment System Admin Portal"
admin.site.index_title = "Escrow Payment System Dashboard"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)