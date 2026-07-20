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

import logging

import anthropic
from pydantic import BaseModel

from core.config import settings
from usuarios.models import TipoCAB

logger = logging.getLogger(__name__)

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


class RiesgoItem(BaseModel):
    riesgo: str
    mitigacion: str


class PasoProceso(BaseModel):
    actor: str
    accion: str
    tipo: str


class CharterContenido(BaseModel):
    justificacion_alcance: str
    objetivos: str
    beneficios_esperados: str
    principales_entregables: str
    riesgos_identificados: list[RiesgoItem]
    estado: str


class BpmnContenido(BaseModel):
    descripcion: str
    actores: list[str]
    pasos_as_is: list[PasoProceso]
    pasos_to_be: list[PasoProceso]


class OnepagerContenido(BaseModel):
    problema: str
    solucion: str
    beneficios: list[str]
    impacto: str
    esfuerzo: str
    proximo_paso: str


class ActividadRaci(BaseModel):
    actividad: str
    roles: dict[str, str]


class RaciContenido(BaseModel):
    actividades: list[ActividadRaci]
    leyenda: dict[str, str]


class BmcContenido(BaseModel):
    segmentos_clientes: str
    propuesta_valor: str
    canales: str
    relaciones_clientes: str
    fuentes_ingreso: str
    recursos_clave: str
    actividades_clave: str
    socios_clave: str
    estructura_costos: str


class BusinessCaseContenido(BaseModel):
    resumen_ejecutivo: str
    problema: str
    solucion_propuesta: str
    costo_estimado: str
    beneficio_estimado: str
    roi_estimado: str
    payback_estimado: str
    supuestos: list[str]
    recomendacion: str


class ContenidoDocumentosMultiple(BaseModel):
    """Wrapper con un sub-modelo opcional por tipo de documento.

    Todos los campos son opcionales porque una misma llamada puede pedir
    1, varios, o los 6 tipos a la vez — Claude deja en null los que no
    se pidieron. El filtro final de "solo devolver lo pedido" es en
    código (ver generar_contenido_documentos), no se confía en que el
    modelo respete esa instrucción del prompt.
    """

    charter: CharterContenido | None = None
    bpmn: BpmnContenido | None = None
    onepager: OnepagerContenido | None = None
    raci: RaciContenido | None = None
    bmc: BmcContenido | None = None
    business_case: BusinessCaseContenido | None = None


_CRITERIOS_DOCUMENTOS = """
Redacta ÚNICAMENTE los campos narrativos (no estructurales) de cada tipo de
documento solicitado, a partir del historial completo de la entrevista.
Deja en null cualquier tipo de documento que NO esté en la lista solicitada
— no lo generes igual. Sé concreto y usa la información real de la
conversación; si algo no se mencionó, usa un texto breve indicando que
falta esa información en vez de inventar datos.

IDIOMA: Siempre en español.
""".strip()


def generar_contenido_documentos(historial: list[dict], tipos: list[str]) -> dict[str, dict]:
    """Genera los campos NARRATIVOS de varios documentos formales en UNA
    sola llamada a Claude — no una llamada por tipo, para no gastar N
    llamadas cuando se piden N documentos a la vez.

    Recibe el historial completo de mensajes_entrevista de la idea (misma
    forma que generar_respuesta). Los campos ESTRUCTURALES (título, autor,
    fechas, quién aprobó) NO pasan por aquí — se toman directo de la base
    de datos en documentos/service.py:_contexto_estructural.

    Devuelve {tipo: dict_de_campos} solo para los `tipos` pedidos.
    """
    if settings.claude_stub_mode:
        return {tipo: _contenido_documento_stub(historial, tipo) for tipo in tipos}

    # Se empaqueta el historial completo como UN solo mensaje de usuario
    # (no como turnos alternados usuario/asistente): messages.parse exige
    # que la conversación termine en un mensaje "user" (no permite
    # "prefill" del turno final, que es donde iría el output_format), y
    # la entrevista real siempre termina con la respuesta del asistente.
    if historial:
        transcripcion = "\n\n".join(
            f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
            for m in historial
        )
    else:
        transcripcion = "(sin mensajes de entrevista registrados)"

    mensajes_anthropic = [
        {
            "role": "user",
            "content": f"Historial completo de la entrevista:\n\n{transcripcion}",
        }
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            max_tokens=4096,
            system=(
                f"Redacta el contenido para estos tipos de documento: {', '.join(tipos)}.\n\n"
                f"{_CRITERIOS_DOCUMENTOS}"
            ),
            messages=mensajes_anthropic,
            output_format=ContenidoDocumentosMultiple,
        )
    except anthropic.APIStatusError as exc:
        # Fallo real de la API: documentos/generadores.py ya usa
        # `.get(clave) or "Pendiente de definir"` en cada campo, así que un
        # dict vacío por tipo es un fallback seguro — el .docx sale con
        # los campos narrativos marcados como pendientes, no rompe nada.
        logger.error("generar_contenido_documentos: fallo de API: %s", exc)
        return {tipo: {} for tipo in tipos}

    parsed = response.parsed_output
    if parsed is None:
        return {tipo: {} for tipo in tipos}

    resultado: dict[str, dict] = {}
    for tipo in tipos:
        sub_modelo = getattr(parsed, tipo, None)
        resultado[tipo] = sub_modelo.model_dump() if sub_modelo else {}
    return resultado


class ClasificacionResultado(BaseModel):
    clasificacion: TipoCAB
    justificacion: str


_CRITERIOS_CLASIFICACION_BASE = """
Clasifica la idea, a partir del historial completo de su entrevista, en
UNA de estas dos categorías (usa exactamente el criterio de negocio que
te doy a continuación, no inventes otro):

- innovacion: ideas de nuevo negocio, nuevas oportunidades, reinventar
  algo — NO es a nivel de proceso interno.
- transformacion_digital: optimizar, digitalizar, transformar, integrar
  o automatizar algo que YA EXISTE en la operación.

Da también una justificación breve y concreta de por qué elegiste esa
categoría, basada en el contenido real de la entrevista.

IDIOMA: Siempre en español.
""".strip()


def clasificar_idea(historial: list[dict], criterio_texto: str) -> dict | None:
    """Clasifica una idea (innovacion vs transformacion_digital) con Structured
    Outputs, a partir del historial de entrevista y el texto del documento de
    criterios activo (subido por Armando vía criterios/).

    Devuelve None si la llamada a la API falla — el caller
    (clasificacion/service.py) debe interpretar eso como "no se pudo
    clasificar automáticamente" y dejar la idea pendiente_clasificacion
    para que un admin la clasifique manualmente. Nunca lanza para un fallo
    de API: eso rompería la transacción de revision/router.py:aprobar, que
    SIEMPRE debe tener éxito aunque la clasificación automática falle.
    """
    if settings.claude_stub_mode:
        return {"clasificacion": TipoCAB.transformacion_digital, "justificacion": "[STUB] clasificación simulada"}

    transcripcion = "\n\n".join(
        f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
        for m in historial
    ) or "(sin mensajes de entrevista registrados)"

    mensajes_anthropic = [
        {
            "role": "user",
            "content": (
                f"Criterio de clasificación definido por el negocio:\n\n{criterio_texto}\n\n"
                f"Historial completo de la entrevista:\n\n{transcripcion}"
            ),
        }
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            max_tokens=1024,
            system=_CRITERIOS_CLASIFICACION_BASE,
            messages=mensajes_anthropic,
            output_format=ClasificacionResultado,
        )
    except anthropic.APIStatusError as exc:
        logger.error("clasificar_idea: fallo de API: %s", exc)
        return None

    parsed = response.parsed_output
    if parsed is None:
        logger.error("clasificar_idea: la respuesta no se pudo parsear contra el schema esperado")
        return None

    return {"clasificacion": parsed.clasificacion, "justificacion": parsed.justificacion}


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
