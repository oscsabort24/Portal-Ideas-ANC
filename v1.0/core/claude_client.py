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
