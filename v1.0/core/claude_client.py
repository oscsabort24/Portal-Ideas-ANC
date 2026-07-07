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
