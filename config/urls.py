from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# El botón "VER SITIO" del admin de Django lleva al dashboard (Next.js en
# Vercel) en vez del backend mismo — así se puede ir y volver entre los dos.
admin.site.site_url = settings.FRONTEND_URL

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("core.urls")),
    path("api/camaras-ia/", include("camaras_ia.urls")),
    path("api/contratistas/", include("contratistas.urls")),
]

# Sirve media/ (snapshots) también fuera de DEBUG — el disco de Railway no
# es persistente entre despliegues; migrar a un storage externo (S3 u otro)
# sigue siendo la decisión pendiente documentada en el README, esto es
# solo lo mínimo para que el dashboard muestre fotos reales mientras tanto.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
