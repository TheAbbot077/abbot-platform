from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/", include("core.urls")),
    path("api/", include("learning.urls")),
    path("api/", include("documents.urls")),
    path("admin/", admin.site.urls),
]
