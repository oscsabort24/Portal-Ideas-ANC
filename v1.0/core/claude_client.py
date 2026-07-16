"""Cliente de la API de Claude (Anthropic).

Mientras CLAUDE_STUB_MODE=true, generar_respuesta() devuelve una respuesta
simulada con la misma forma que la respuesta real, para que el resto de
módulos (ideas/, clasificacion/, revision/) puedan integrarse contra esta
interfaz sin depender de la API real.

Con CLAUDE_STUB_MODE=false, usa Structured Outputs del SDK de Anthropic
(client.messages.parse + output_format) para garantizar JSON válido — la
API valida la respuesta contra el schema Pydantic, en vez de confiar en
que el modelo respete instrucciones de formato en texto libre.
"""

import anthropic
from pydantic import BaseModel

from core.config import settings

_client = anthropic.Anthropic(api_key=settings.claude_api_key)


class RespuestaEntrevista(BaseModel):
    message: str
    entrevista_completa: bool
    options: list[str] | None


_CRITERIOS_ENTREVISTA = """
━━━ 5 BLOQUES DE INFORMACIÓN (TODOS OBLIGATORIOS) ━━━
Cúbrelos en el orden más natural según lo que la persona ya dijo — no es un
formulario paso a paso, es una conversación.

BLOQUE 1 — Problema y Alcance
- Qué pasa hoy, qué proceso o tarea se quiere mejorar
- Si la respuesta es vaga, pide un ejemplo concreto antes de continuar

BLOQUE 2 — Objetivo Medible
- Qué cambiaría concretamente si esto se implementa
- Si no hay nada medible, ofrece sugerencias (ahorrar tiempo, reducir errores,
  ahorrar dinero, mejorar experiencia) y pregunta la magnitud estimada

BLOQUE 3 — Beneficios Esperados
- Compara cuánto tiempo/costo toma el proceso HOY vs. con la idea implementada
- Pide números aunque sean estimaciones aproximadas

BLOQUE 4 — Entregables Principales
- Qué se imagina recibiendo si esto se aprueba (reporte, alerta, sistema, etc.)
- Este bloque es OBLIGATORIO — no marques la entrevista como completa sin él

BLOQUE 5 — Riesgos y Mitigación
- Qué podría complicar que esto funcione
- Si la persona no ve riesgos, sugiere 2-3 típicos según el tipo de idea
- Este bloque es OBLIGATORIO — no marques la entrevista como completa sin él

━━━ REGLA DE CIERRE ━━━
Los 5 bloques deben tener contenido SUSTANTIVO (no solo mencionados de pasada)
para marcar entrevista_completa = true. Mientras falte alguno, sigue
preguntando — una sola pregunta a la vez, cálido pero exigente con la
concreción de las respuestas.

IDIOMA: Siempre en español.
""".strip()

_RESPUESTA_DEGRADADA_API = {
    "message": "Hubo un problema técnico al procesar tu respuesta. Intenta de nuevo en un momento.",
    "entrevista_completa": False,
    "options": None,
    "raw": None,
}

_RESPUESTA_DEGRADADA_SIN_PARSEAR = {
    "message": "No se pudo procesar la respuesta de la IA. Intenta de nuevo.",
    "entrevista_completa": False,
    "options": None,
    "raw": None,
}


def generar_respuesta(mensajes: list[dict], system_prompt: str) -> dict:
    if settings.claude_stub_mode:
        return _respuesta_stub(mensajes, system_prompt)

    mensajes_anthropic = [
        {"role": "assistant" if m["role"] == "asistente" else "user", "content": m["content"]}
        for m in mensajes
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            max_tokens=1024,
            system=f"{system_prompt}\n\n{_CRITERIOS_ENTREVISTA}",
            messages=mensajes_anthropic,
            output_format=RespuestaEntrevista,
        )
    except anthropic.APIStatusError:
        # Fallo real de la API (rate limit, 5xx, etc.) — no rompe la
        # conversación, degrada a un mensaje visible para reintentar.
        return dict(_RESPUESTA_DEGRADADA_API)

    parsed = response.parsed_output
    if parsed is None:
        # parsed_output puede ser None si Claude no generó un bloque de
        # texto parseable (ej. stop_reason distinto a end_turn) — ver
        # anthropic/types/parsed_message.py, es una @property, no un campo
        # garantizado.
        return dict(_RESPUESTA_DEGRADADA_SIN_PARSEAR)

    return {
        "message": parsed.message,
        "entrevista_completa": parsed.entrevista_completa,
        "options": parsed.options,
        "raw": None,
    }


def generar_contenido_documento(historial: list[dict], tipo_documento: str) -> dict:
    """Genera los campos NARRATIVOS de uno de los 6 documentos formales.

    Recibe el historial completo de mensajes_entrevista de la idea (misma
    forma que generar_respuesta: [{"role": "usuario"|"asistente", "content": str}]).
    Los campos ESTRUCTURALES (título, autor, fechas, quién aprobó) NO pasan
    por aquí — se toman directo de la base de datos en
    documentos/service.py:_contexto_estructural.
    """
    if settings.claude_stub_mode:
        return _contenido_documento_stub(historial, tipo_documento)

    raise NotImplementedError(
        "Integración real con Claude API pendiente de aprobación de presupuesto. "
        "Set CLAUDE_STUB_MODE=true mientras tanto."
    )


TURNOS_USUARIO_PARA_COMPLETAR_STUB = 3


def _respuesta_stub(mensajes: list[dict], system_prompt: str) -> dict:
    turnos_usuario = sum(1 for m in mensajes if m.get("role") == "usuario")
    entrevista_completa = turnos_usuario >= TURNOS_USUARIO_PARA_COMPLETAR_STUB

    if entrevista_completa:
        mensaje = "[STUB] Entrevista simulada completa — la idea tiene suficiente detalle."
    else:
        mensaje = (
            "[STUB] Respuesta simulada — dame un ejemplo más concreto "
            f"(turno {turnos_usuario} de {TURNOS_USUARIO_PARA_COMPLETAR_STUB})."
        )

    return {
        "message": mensaje,
        "entrevista_completa": entrevista_completa,
        "options": None,
        "raw": None,
    }


def _contenido_documento_stub(historial: list[dict], tipo_documento: str) -> dict:
    """Contenido narrativo simulado, marcado [STUB] en cada campo.

    No inventa contenido creíble a partir del historial — deja explícito
    que es simulado, igual que _respuesta_stub, hasta que haya presupuesto
    para conectar la API real de Claude.
    """
    turnos_usuario = sum(1 for m in historial if m.get("role") == "usuario")
    resumen = f"[STUB] Contenido generado a partir de {turnos_usuario} mensaje(s) de la entrevista."

    generadores = {
        "charter": lambda: {
            "justificacion_alcance": resumen,
            "objetivos": resumen,
            "beneficios_esperados": resumen,
            "principales_entregables": resumen,
            "riesgos_identificados": [
                {"riesgo": "[STUB] Riesgo identificado de ejemplo", "mitigacion": "[STUB] Mitigación de ejemplo"}
            ],
            "estado": "Listo para revisión",
        },
        "bpmn": lambda: {
            "descripcion": resumen,
            "actores": ["[STUB] Actor 1", "[STUB] Actor 2"],
            "pasos_as_is": [{"actor": "[STUB] Actor 1", "accion": "[STUB] Paso actual de ejemplo", "tipo": "tarea"}],
            "pasos_to_be": [{"actor": "[STUB] Actor 1", "accion": "[STUB] Paso futuro de ejemplo", "tipo": "tarea"}],
        },
        "onepager": lambda: {
            "problema": resumen,
            "solucion": resumen,
            "beneficios": ["[STUB] Beneficio 1", "[STUB] Beneficio 2"],
            "impacto": "Por definir",
            "esfuerzo": "Por definir",
            "proximo_paso": resumen,
        },
        "raci": lambda: {
            "actividades": [{"actividad": "[STUB] Actividad de ejemplo", "roles": {"Solicitante": "R"}}],
            "leyenda": {
                "R": "Responsable — quien ejecuta",
                "A": "Aprobador — quien aprueba y rinde cuentas",
                "C": "Consultado — quien da input",
                "I": "Informado — quien recibe updates",
            },
        },
        "bmc": lambda: {
            "segmentos_clientes": resumen,
            "propuesta_valor": resumen,
            "canales": resumen,
            "relaciones_clientes": resumen,
            "fuentes_ingreso": resumen,
            "recursos_clave": resumen,
            "actividades_clave": resumen,
            "socios_clave": resumen,
            "estructura_costos": resumen,
        },
        "business_case": lambda: {
            "resumen_ejecutivo": resumen,
            "problema": resumen,
            "solucion_propuesta": resumen,
            "costo_estimado": "Por definir",
            "beneficio_estimado": "Por definir",
            "roi_estimado": "Por definir",
            "payback_estimado": "Por definir",
            "supuestos": ["[STUB] Supuesto de ejemplo"],
            "recomendacion": "Pendiente de análisis",
        },
    }

    return generadores[tipo_documento]()
