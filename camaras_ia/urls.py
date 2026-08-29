from django.urls import path

from . import views

app_name = "camaras_ia"

urlpatterns = [
    path("eventos/", views.recibir_evento_camara, name="recibir_evento_camara"),
]
