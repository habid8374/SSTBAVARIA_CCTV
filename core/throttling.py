from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limita los intentos de login por IP para dificultar la fuerza bruta
    de contraseñas. Solo se aplica al endpoint de login — no al resto de la
    API — para no arriesgar interferir con el polling normal del equipo
    local ni de otras integraciones."""

    scope = "login"
