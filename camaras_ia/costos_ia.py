"""Consumo de la API de Claude: tokens de cada llamada, su costo estimado en
USD y el tope de gasto configurable (ConfiguracionIA.tope_usd).

El costo es una estimación con la tarifa pública de cada modelo — la cifra
oficial es la de la consola de Anthropic. Por eso conviene configurar
también allá un límite de gasto como respaldo.
"""

import logging
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import ConfiguracionIA, ConsumoIA

logger = logging.getLogger("camaras_ia.costos_ia")

UN_MILLON = Decimal("1000000")

# USD por millón de tokens: (entrada, salida, lectura de caché). Tarifas de la
# API de Anthropic vigentes a 2026-09. La escritura en caché cuesta 1.25x la
# entrada (caché de 5 minutos).
PRECIOS_CLAUDE_USD_POR_MTOK = {
    "claude-fable-5-1": (Decimal("10"), Decimal("50"), Decimal("0.25")),
    "claude-fable-5": (Decimal("10"), Decimal("50"), Decimal("1.00")),
    "claude-opus-5-5": (Decimal("4"), Decimal("20"), Decimal("0.20")),
    "claude-opus-5": (Decimal("5"), Decimal("25"), Decimal("0.50")),
    "claude-opus-4-8": (Decimal("5"), Decimal("25"), Decimal("0.50")),
    "claude-opus-4-7": (Decimal("5"), Decimal("25"), Decimal("0.50")),
    "claude-opus-4-6": (Decimal("5"), Decimal("25"), Decimal("0.50")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10"), Decimal("0.20")),
    "claude-sonnet-5": (Decimal("2"), Decimal("10"), Decimal("0.20")),
    "claude-sonnet-4-6": (Decimal("3"), Decimal("15"), Decimal("0.30")),
    "claude-haiku-4-5": (Decimal("1"), Decimal("5"), Decimal("0.10")),
}
FACTOR_ESCRITURA_CACHE = Decimal("1.25")

# Un modelo que no está en la tabla se cobra con la tarifa más alta, para que
# el tope nunca se quede corto por subestimar el gasto.
PRECIO_DESCONOCIDO = max(PRECIOS_CLAUDE_USD_POR_MTOK.values())

UMBRAL_AVISO = Decimal("0.8")


def precio_modelo(modelo):
    """Busca por prefijo más largo, así un ID con fecha (ej.
    claude-haiku-4-5-20251001) usa la tarifa de su modelo base."""
    coincidencias = [clave for clave in PRECIOS_CLAUDE_USD_POR_MTOK if modelo.startswith(clave)]
    if not coincidencias:
        logger.warning("Modelo %r sin tarifa conocida — se estima con la tarifa más alta.", modelo)
        return PRECIO_DESCONOCIDO
    return PRECIOS_CLAUDE_USD_POR_MTOK[max(coincidencias, key=len)]


def calcular_costo_usd(modelo, tokens_entrada, tokens_salida, tokens_cache_escritura=0, tokens_cache_lectura=0):
    entrada, salida, cache_lectura = precio_modelo(modelo)
    total = (
        tokens_entrada * entrada
        + tokens_salida * salida
        + tokens_cache_escritura * entrada * FACTOR_ESCRITURA_CACHE
        + tokens_cache_lectura * cache_lectura
    )
    return total / UN_MILLON


def gasto_del_periodo_usd(config=None):
    config = config or ConfiguracionIA.obtener()
    consumos = ConsumoIA.objects.all()
    if config.consumo_desde:
        consumos = consumos.filter(creado_en__gte=config.consumo_desde)
    return consumos.aggregate(total=Sum("costo_usd"))["total"] or Decimal("0")


def registrar_consumo(modelo, usage, evento=None):
    """Guarda una llamada a partir de `respuesta.usage` del SDK de Anthropic
    y avisa al personal interno al cruzar el 80% y el 100% del tope."""
    tokens = {
        "tokens_entrada": usage.input_tokens,
        "tokens_salida": usage.output_tokens,
        # El SDK los deja en None cuando la llamada no usó caché.
        "tokens_cache_escritura": usage.cache_creation_input_tokens or 0,
        "tokens_cache_lectura": usage.cache_read_input_tokens or 0,
    }
    config = ConfiguracionIA.obtener()
    gasto_antes = gasto_del_periodo_usd(config)
    consumo = ConsumoIA.objects.create(
        modelo=modelo,
        evento=evento,
        costo_usd=calcular_costo_usd(modelo, **tokens),
        **tokens,
    )
    _avisar_si_cruza_umbral(config, gasto_antes, gasto_antes + consumo.costo_usd)
    return consumo


def _avisar_si_cruza_umbral(config, gasto_antes, gasto_despues):
    from core.push import enviar_push_a_personal_interno

    tope = config.tope_usd
    if gasto_antes < tope <= gasto_despues:
        titulo = "GuardIA — tope de IA alcanzado"
        cuerpo = f"Se gastaron USD {gasto_despues:.2f} de USD {tope:.2f}. La clasificación con IA quedó pausada."
    elif gasto_antes < tope * UMBRAL_AVISO <= gasto_despues:
        titulo = "GuardIA — consumo de IA al 80%"
        cuerpo = f"Se gastaron USD {gasto_despues:.2f} de USD {tope:.2f}."
    else:
        return
    enviar_push_a_personal_interno(titulo, cuerpo, url="/dashboard?ir=sistema")


def reiniciar_periodo(config=None):
    config = config or ConfiguracionIA.obtener()
    config.consumo_desde = timezone.now()
    config.save(update_fields=["consumo_desde", "actualizada_en"])
    return config
