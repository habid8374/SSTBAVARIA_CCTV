from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EquipoLocal


@api_view(["POST"])
def recibir_evento_camara(request):
    """Stub del endpoint que el equipo local usará para reportar eventos.

    Valida la API key del EquipoLocal (header X-API-Key) y responde 201.
    La lógica de cruce zona+horario (evaluar_zona_horario) y el guardado del
    EventoDetectado se implementan en la Fase 2, cuando haya conexión real
    a cámaras.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key or not EquipoLocal.objects.filter(api_key=api_key, activo=True).exists():
        return Response(
            {"detail": "API key inválida o inactiva."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({"detail": "Evento recibido."}, status=status.HTTP_201_CREATED)
