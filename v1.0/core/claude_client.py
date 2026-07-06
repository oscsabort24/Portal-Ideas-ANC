"""Cliente de la API de Claude (Anthropic).

Mientras CLAUDE_STUB_MODE=true (pendiente de aprobación de presupuesto),
generar_respuesta() devuelve una respuesta simulada con la misma forma
que tendrá la respuesta real, para que el resto de módulos (ideas/,
clasificacion/, revision/) puedan integrarse contra esta interfaz sin
esperar a que la integración real esté lista.
"""

from core.config import settings


def generar_respuesta(mensajes: list[dict], system_prompt: str) -> dict:
    if settings.claude_stub_mode:
        return _respuesta_stub(mensajes, system_prompt)

    raise NotImplementedError(
        "Integración real con Claude API pendiente de aprobación de presupuesto. "
        "Set CLAUDE_STUB_MODE=true mientras tanto."
    )


def _respuesta_stub(mensajes: list[dict], system_prompt: str) -> dict:
    return {
        "message": "[STUB] Respuesta simulada — la integración real con Claude API aún no está activa.",
        "options": None,
        "raw": None,
    }
