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
from enum import Enum
from typing import Literal

import anthropic
import httpx
from pydantic import BaseModel, Field, ValidationError, create_model

from core.config import settings
from usuarios.models import TipoCAB

logger = logging.getLogger(__name__)

# timeout y max_retries EXPLÍCITOS. Los defaults del SDK 0.116.0 son
# Timeout(connect=5, read=600, write=600, pool=600) y max_retries=2, o sea
# que una sola llamada puede tardar hasta ~30 minutos. El frontend aborta a
# los 40 s (ChatEntrevista.tsx:TIMEOUT_ENVIO_MS), así que sin esto el backend
# sigue trabajando —ocupando un hilo del threadpool, porque el endpoint es
# sync (ideas/router.py:enviar_mensaje)— mucho después de que la persona ya
# vio un error.
#
# Presupuesto por debajo de esos 40 s, para que la persona reciba una
# respuesta degradada real en vez de un abort del navegador:
#   intento 1 (read)        12.0 s
#   backoff del SDK          0.5 s  (máx.; ver cálculo abajo)
#   intento 2 (read)        12.0 s
#   ───────────────────────────────
#   peor caso típico       ~24.5 s
#
# El backoff sale de _base_client.py:_calculate_retry_timeout:
#   nb_retries = max_retries - remaining_retries = 0 en el primer reintento
#   sleep = min(INITIAL_RETRY_DELAY * 2**0, MAX_RETRY_DELAY) = 0.5 s
#   jitter = 1 - 0.25*random()  ->  (0.75, 1.0]
#   backoff real ∈ (0.375, 0.5] s
#
# EXCEPCIÓN conocida: si la API responde con cabecera `retry-after`, el SDK
# la obedece tal cual hasta 60 s (_base_client.py:826-829) e ignora el
# backoff exponencial. Eso pasa en un 429 por rate limit y puede empujar el
# total a ~85 s. No se puede acotar desde acá; en ese caso el abort del
# frontend a los 40 s es la red de contención, y la persona ve un error
# limpio en vez de un cuelgue. Reintentar rápido un 429 tampoco ayudaría.
_client = anthropic.Anthropic(
    api_key=settings.claude_api_key,
    timeout=httpx.Timeout(connect=5.0, read=12.0, write=10.0, pool=5.0),
    max_retries=1,
)


class EstadoBloque(str, Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completado = "completado"


class ProgresoBloques(BaseModel):
    problema_alcance: EstadoBloque
    objetivo_medible: EstadoBloque
    beneficios: EstadoBloque
    entregables: EstadoBloque
    riesgos: EstadoBloque


_PROGRESO_BLOQUES_PENDIENTE = {
    "problema_alcance": EstadoBloque.pendiente.value,
    "objetivo_medible": EstadoBloque.pendiente.value,
    "beneficios": EstadoBloque.pendiente.value,
    "entregables": EstadoBloque.pendiente.value,
    "riesgos": EstadoBloque.pendiente.value,
}

_PROGRESO_BLOQUES_COMPLETO = {clave: EstadoBloque.completado.value for clave in _PROGRESO_BLOQUES_PENDIENTE}


class RespuestaEntrevista(BaseModel):
    # min_length: en pruebas reales el modelo devolvió `message` vacío al
    # menos una vez (respuesta del usuario desalineada con la pregunta en
    # curso), y eso pintaba una burbuja en blanco en el chat. El mínimo
    # empuja a la API a generar contenido.
    #
    # OJO: si aun así viene vacío, esta restricción hace que el SDK lance
    # ValidationError DENTRO de messages.parse(), así que la ejecución nunca
    # llega al chequeo de `mensaje vacío` de generar_respuesta más abajo —
    # ese chequeo quedó como defensa para un `message` que sea solo espacios
    # (pasa min_length pero queda vacío tras .strip()). El caso realmente
    # vacío lo cubre el `except ValidationError`.
    message: str = Field(min_length=1)
    entrevista_completa: bool
    options: list[str] | None
    progreso_bloques: ProgresoBloques


_CRITERIOS_ENTREVISTA = """
━━━ CÓMO HABLÁS ━━━
Estas reglas van ANTES que cualquier otra cosa. Si alguna instrucción de
abajo choca con estas, ganan estas.

1. UNA SOLA PREGUNTA POR TURNO. Nunca dos, nunca "y además". Si necesitás
   tres datos, son tres turnos. Un mensaje tuyo = una frase de contexto
   (opcional) + una pregunta.
2. Hay palabras de oficina que la persona no usa. Cuando te salga una,
   decila así en su lugar:
     bloque / tema / etapa      -> no lo nombres, pasá directo a la pregunta
     alcance                    -> "a quiénes les pasa"
     objetivo medible           -> "qué mejoraría"
     entregable                 -> "qué te gustaría recibir"
     mitigación                 -> "cómo evitarlo"
     canal                      -> "cómo lo pedís"
     recursos / actividades     -> "qué se necesita" / "qué habría que hacer"
     socio clave                -> "alguien de fuera de la empresa"
     iniciativa / propuesta     -> "tu idea"
   Y estas nunca aparecen en un mensaje tuyo, ni de pasada: stakeholder,
   KPI, ROI, segmento, business model canvas, BMC, RICE, priorización,
   gobernanza, CAB, política, entrevista.
   Tampoco anuncies de qué vas a hablar ("ahora te pregunto sobre X") —
   simplemente hacé la pregunta.
3. Antes de mandar tu mensaje, releelo: tiene que ser una frase que le
   dirías en voz alta a un compañero. Si quedó cortado, repetido o sin
   sentido, reescribilo.
4. Cada pregunta lleva un EJEMPLO CORTO entre paréntesis, para que la
   persona vea qué tipo de respuesta esperás. Ej: "¿cuánto tiempo te lleva
   hacer eso hoy? (una hora, media mañana, todo el día...)".
5. Voseo costarricense, siempre. "contame", "¿te pasa seguido?", "¿querés".
   Nunca "cuéntame" ni "¿quieres?".
6. Frases cortas. Máximo 3 o 4 líneas por mensaje.
7. Reconocé lo que la persona te dijo antes de preguntar lo siguiente
   ("Buenísimo, o sea que hoy lo hacen a mano..."). No saltes de pregunta
   en pregunta como un formulario.

━━━ QUÉ HACER CON RESPUESTAS CORTAS O VAGAS ━━━
Una respuesta corta NO es un problema. La persona está trabajando, no
llenando un informe.

- Primera vez que algo queda vago: reformulá UNA vez, más fácil y con un
  ejemplo o con opciones para elegir. Nunca digas que la respuesta es
  insuficiente, vaga, incompleta, ni le pidas que "sea más concreta".
- Si en ese segundo intento sigue sin saber: DALO POR BUENO. Anotá "no lo
  sabe / por definir" y pasá al siguiente tema. No insistas una tercera vez.
  Un tema con "no lo sabe" cuenta igual como "completado".
- "No sé", "no tengo idea", "eso lo ve otra área" son respuestas VÁLIDAS y
  útiles. Agradecelas ("dale, sin problema") y seguí.
- Nunca corrijas cómo escribió algo ni pidas que lo reformule.

━━━ LOS 5 TEMAS A CUBRIR (nombres internos, no los digas) ━━━
Cubrilos en el orden que fluya según lo que la persona ya contó. Cada
viñeta de abajo es UN turno distinto.

TEMA 1 — problema_alcance
· Qué le pasa hoy en el trabajo, qué le gustaría que fuera más fácil.
  Si contesta muy general, pedí que te cuente la última vez que le pasó.
· A quiénes más les pasa: "¿esto te pasa solo a vos y tu equipo, o también
  en otras áreas? (Operaciones, Servicio al Cliente, TI...)"
· En qué países: "¿esto pasaría solo en Costa Rica, o también en Guatemala,
  Nicaragua o Perú?"
· Cuánto podría costar. Preguntalo así de simple: "¿tenés una idea de
  cuánta plata haría falta? Si no, no importa — elegí lo que te suene más
  cercano." Y ofrecé estas 5 opciones EXACTAS en el campo `options`:
  "Nada — lo haríamos con personal ANC", "Hasta $10,000",
  "Entre $10,000 y $20,000", "Entre $20,000 y $30,000", "Más de $30,000".
  OJO: la primera es el tramo de costo CERO, no una respuesta sobre quién
  ejecuta — los otros cuatro son montos y la escala tiene que seguir siendo
  de plata. Dice con qué personal para explicar por qué no cuesta.
· Cuánto tiempo tomaría hacerlo, con estas 3 opciones EXACTAS en `options`:
  "Menos de 6 meses", "Entre 6 meses y un año", "Más de un año".
· Si hace falta gente de afuera — OPCIONAL, preguntalo solo si la idea
  suena a que depende de alguien externo: "¿esto necesitaría a alguien de
  fuera de la empresa? (un proveedor de sistemas, un banco, una empresa de
  transporte...)". Si dice que no, o si es claramente algo interno, anotá
  que se hace todo en casa y seguí. Ojo: esto es gente de FUERA de ANC, no
  las áreas internas de la pregunta de arriba.

TEMA 2 — objetivo_medible
· Qué cambiaría si esto existiera: "si esto ya estuviera funcionando,
  ¿qué sería distinto en tu día?"
· Si no se le ocurre nada, ofrecé opciones en `options`: "Ahorrar tiempo",
  "Cometer menos errores", "Gastar menos plata", "Que el cliente esté más
  contento". Después preguntá cuánto, más o menos — y si no sabe, seguí.

TEMA 3 — beneficios
· Cuánto tiempo o esfuerzo toma hoy: "¿cuánto te lleva hacerlo ahora?
  (10 minutos, media mañana, todo el día...)"
· Cuánto tomaría con la idea funcionando. Un número aproximado alcanza; si
  no lo tiene, un "mucho menos" también sirve.
· Cómo se pide o se resuelve hoy — OPCIONAL, solo si viene al caso:
  "¿cómo lo pedís hoy? (por WhatsApp, por correo, llamando...)" y cómo te
  gustaría que fuera.
· Quién ayuda cuando algo sale mal — OPCIONAL, solo si la idea es algo que
  otra gente va a usar: "¿la persona lo resolvería sola, o necesitaría que
  alguien la ayude?"

TEMA 4 — entregables
· Qué le gustaría tener en las manos: "si esto se aprueba, ¿qué te
  gustaría recibir? (un reporte, una alerta al celular, una pantalla donde
  ver todo...)"
· Qué haría falta para armarlo — OPCIONAL: "¿qué se necesitaría? (que
  alguien de sistemas lo programe, una app, capacitar a la gente...)"

TEMA 5 — riesgos
· Qué podría salir mal: "¿qué se te ocurre que podría complicar esto?"
· Si no se le ocurre nada, sugerí vos 2 o 3 típicos según la idea y
  preguntá si alguno le suena. Si dice que ninguno, dalo por bueno y
  anotá los que sugeriste.
· Si menciona algo que podría salir mal, preguntá si se le ocurre cómo
  evitarlo — pero si no sabe, no insistas.

━━━ CUÁNDO USAR `options` ━━━
Llená `options` con 2 a 5 respuestas cortas para elegir SIEMPRE que la
pregunta tenga opciones cerradas (plata, tiempo, países, tipo de mejora) o
que la persona haya dicho que no sabe. La pantalla las muestra como botones
para tocar, así no tiene que escribir. Fuera de esos casos, dejalo en null:
una pregunta abierta con botones limita la respuesta.

Si la pregunta se responde con sí o no (ej. si hace falta alguien de fuera
de la empresa, si le suena alguno de los riesgos que sugeriste), poné
opciones tipo "Sí", "No" y "No estoy seguro" — y hacé la pregunta SIMPLE,
sin agregarle la alternativa a mano ("...o si se resuelve internamente,
contame"): eso ya lo cubren los botones y convierte una pregunta en dos.

━━━ CIERRE ━━━
Los 5 temas necesitan tener ALGO anotado — incluido "no lo sabe" — antes de
darlos por listos. Vos NUNCA cerrás ni enviás nada: cuando los 5 estén
listos, decilo así, sin nombrar la estructura interna:
"¡Listo, ya tengo todo lo que necesitaba! ¿Querés agregar algo más, o lo
mandamos ya con el botón 'Enviar idea'?"
Y seguí disponible por si quiere agregar más. Quien decide enviar es la
persona, con un botón en la pantalla — no vos. Por eso
entrevista_completa SIEMPRE va en false, sin excepción; ese campo ya no
dispara ningún envío automático.

━━━ PROGRESO POR TEMA (progreso_bloques) ━━━
En CADA turno evaluá el estado de los 5 temas (problema_alcance,
objetivo_medible, beneficios, entregables, riesgos) según TODO lo que la
persona dijo en la conversación, no solo el último mensaje:
- "pendiente": todavía no se habló nada de ese tema.
- "en_progreso": se tocó el tema pero falta alguna de sus preguntas.
- "completado": ya se preguntó lo del tema y hay una respuesta — aunque esa
  respuesta sea "no lo sabe". Las preguntas marcadas OPCIONAL arriba NO son
  requisito para marcar un tema como completado.
Este dato es el que la pantalla usa para el avance y para habilitar el
botón "Enviar idea", así que no dejes un tema en "en_progreso" si ya
preguntaste todo lo suyo y la persona respondió algo.

IDIOMA: Siempre en español, voseo.
""".strip()

_RESPUESTA_DEGRADADA_API = {
    "message": "Hubo un problema técnico al procesar tu respuesta. Intenta de nuevo en un momento.",
    "entrevista_completa": False,
    "options": None,
    "progreso_bloques": None,
    "raw": None,
    "degradado": True,
}

_RESPUESTA_DEGRADADA_SIN_PARSEAR = {
    "message": "No se pudo procesar la respuesta de la IA. Intenta de nuevo.",
    "entrevista_completa": False,
    "options": None,
    "progreso_bloques": None,
    "raw": None,
    "degradado": True,
}

# Cuando la IA devuelve un JSON que no valida contra RespuestaEntrevista
# (típicamente `message` vacío), la persona no debería ver un error de
# sistema: desde su lado esto es una conversación, no una transacción que
# falló. Se repregunta y la entrevista sigue viva.
_RESPUESTA_REPREGUNTA = {
    "message": "Perdón, se me fue la idea. ¿Me lo repetís?",
    "entrevista_completa": False,
    "options": None,
    "progreso_bloques": None,
    "raw": None,
    "degradado": True,
}


def _criterio_entrevista_departamento(departamento_id: int | None) -> str | None:
    """Ajuste ADITIVO al prompt de entrevista según el departamento del
    autor de la idea — nunca sustituye _CRITERIOS_ENTREVISTA, solo se le
    agrega al final. Fila específica del departamento gana; si no existe,
    cae al default (departamento_id NULL). Import local de
    core.database/criterios.models para evitar un ciclo de imports (este
    módulo no importa nada de criterios/ a nivel de módulo)."""
    from core.database import SessionLocal
    from criterios.models import CriterioIA, TipoCriterio

    db = SessionLocal()
    try:
        especifico = (
            db.query(CriterioIA)
            .filter_by(tipo=TipoCriterio.entrevista, departamento_id=departamento_id, activo=True)
            .first()
            if departamento_id is not None
            else None
        )
        if especifico:
            return especifico.contenido
        default = (
            db.query(CriterioIA)
            .filter_by(tipo=TipoCriterio.entrevista, departamento_id=None, activo=True)
            .first()
        )
        return default.contenido if default else None
    finally:
        db.close()


def _construir_system_entrevista(system_prompt: str, departamento_id: int | None) -> str:
    base = f"{system_prompt}\n\n{_CRITERIOS_ENTREVISTA}"
    ajuste = _criterio_entrevista_departamento(departamento_id)
    return f"{base}\n\n{ajuste}" if ajuste else base


def generar_respuesta(mensajes: list[dict], system_prompt: str, departamento_id: int | None) -> dict:
    if settings.claude_stub_mode:
        return _respuesta_stub(mensajes, system_prompt)

    mensajes_anthropic = [
        {"role": "assistant" if m["role"] == "asistente" else "user", "content": m["content"]}
        for m in mensajes
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            # 4096, no 1024: en Sonnet 5 OMITIR `thinking` activa razonamiento
            # adaptativo (en Sonnet 4.6 omitirlo significaba "sin
            # razonamiento"), y max_tokens limita razonamiento + texto JUNTOS.
            # Con 1024 el presupuesto se agotaba mientras el decodificador
            # estaba restringido por el grammar del Structured Output, y salían
            # turnos con el texto destrozado ("¡ Buen ísimo Ideal ! , U so na
            # na aler ta cu cuando...") o un `message` vacío — ambos
            # reproducidos y guardados en BD, ver idea de prueba 36.
            #
            # thinking deshabilitado: un turno de entrevista es una pregunta
            # corta, no necesita razonamiento extendido — y al deshabilitarlo
            # el decodificador ya no compite por presupuesto con el grammar
            # del Structured Output, que era la causa del texto destrozado
            # descrito arriba.
            thinking={"type": "disabled"},
            max_tokens=4096,
            system=_construir_system_entrevista(system_prompt, departamento_id),
            messages=mensajes_anthropic,
            output_format=RespuestaEntrevista,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        # Fallo real de la API (rate limit, 5xx, timeout, red, etc.) — no
        # rompe la conversación, degrada a un mensaje visible para reintentar.
        logger.error("generar_respuesta: fallo de API: %s", exc)
        return dict(_RESPUESTA_DEGRADADA_API)
    except ValidationError as exc:
        # El SDK valida el JSON contra RespuestaEntrevista DENTRO de
        # messages.parse(), así que un `message` vacío revienta acá arriba y
        # jamás alcanza el chequeo de mensaje vacío de más abajo — ese
        # fallback estaba muerto para este caso, y la persona terminaba
        # viendo "Hubo un problema técnico" (traceback real observado en
        # producción el 2026-08-25).
        #
        # Va ANTES del `except Exception`: ValidationError hereda de
        # ValueError -> Exception, así que si se invierte el orden esta rama
        # nunca se ejecuta.
        logger.warning("generar_respuesta: la IA devolvió un JSON inválido: %s", exc)
        return dict(_RESPUESTA_REPREGUNTA)
    except Exception:
        # Red de seguridad: cualquier excepción no prevista que llegue hasta
        # acá sin atrapar se propagaría sin manejar hasta el router y
        # terminaría en un 500 fuera del stack de CORSMiddleware — el
        # navegador lo reporta como error de CORS en vez de como el fallo
        # real que es (ver diagnóstico de ideas/router.py:preguntar).
        logger.exception("generar_respuesta: excepción no prevista")
        return dict(_RESPUESTA_DEGRADADA_API)

    parsed = response.parsed_output
    if parsed is None:
        # parsed_output puede ser None si Claude no generó un bloque de
        # texto parseable (ej. stop_reason distinto a end_turn) — ver
        # anthropic/types/parsed_message.py, es una @property, no un campo
        # garantizado.
        return dict(_RESPUESTA_DEGRADADA_SIN_PARSEAR)

    # Última red: un `message` vacío o en blanco se guardaría como un
    # MensajeEntrevista sin contenido y el chat pintaría una burbuja vacía,
    # que para la persona se lee como que la IA se colgó. Se sustituye por
    # una repregunta neutra que mantiene la conversación viva; el progreso
    # de bloques del turno SÍ se conserva, que es dato válido.
    mensaje = parsed.message.strip()
    degradado = False
    if not mensaje:
        logger.warning("generar_respuesta: la IA devolvió un mensaje vacío; se usó el texto de respaldo")
        mensaje = "Perdón, se me fue la idea. ¿Me lo repetís?"
        # Este turno tampoco es contenido real de la IA: se marca degradado
        # para que no vuelva como contexto (ver ideas/service.py:historial_para_ia).
        degradado = True

    return {
        "message": mensaje,
        "entrevista_completa": parsed.entrevista_completa,
        "options": parsed.options,
        "progreso_bloques": parsed.progreso_bloques.model_dump(),
        "raw": None,
        "degradado": degradado,
    }


class RiesgoItem(BaseModel):
    riesgo: str
    mitigacion: str


class PasoProceso(BaseModel):
    actor: str
    accion: str
    tipo: str
    # Solo aplica a pasos de `pasos_as_is`: marca si ese paso del proceso
    # actual desaparece en el rediseño TO-BE (para pintarlo distinto en el
    # diagrama). En `pasos_to_be` siempre va True — todo paso ahí SÍ se usa.
    usado_en_to_be: bool = True


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
    """`asignaciones` es un string, no un dict[str,str] ni list[objeto]:
    en pruebas reales un dict[str,str] libre volvía SIEMPRE {} (el
    Structured Output de Anthropic no fuerza contenido en propiedades
    abiertas) y list[objeto-con-2-props] hacía que el schema combinado de
    los 6 tipos de documento superara el límite de tamaño de grammar
    ("compiled grammar is too large" — 400). Un string obligatorio SÍ
    fuerza contenido, y no agrega ningún nodo de grammar nuevo. Formato:
    "Rol A: R; Rol B: A; Rol C: C" — se parsea a dict en
    generar_contenido_documentos()."""

    actividad: str
    asignaciones: str


class RaciContenido(BaseModel):
    """`leyenda` no es un campo del modelo: las definiciones de R/A/C/I son
    siempre las mismas sin importar la idea, así que se hardcodean en
    _LEYENDA_RACI en vez de pedírselas al modelo — un campo dict[str,str]
    ahí volvía siempre {} (ver docstring de ActividadRaci) y agregarlo como
    objeto de propiedades fijas hacía que el schema combinado de los 6
    tipos de documento superara el límite de tamaño de grammar de la API
    ("compiled grammar is too large", 400)."""

    actividades: list[ActividadRaci]


_LEYENDA_RACI = {
    "R": "Responsable — ejecuta la actividad",
    "A": "Aprueba — autoriza y rinde cuentas",
    "C": "Consultado — se le pide opinión antes de actuar",
    "I": "Informado — se le comunica el resultado",
}


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

━━━ SI SE PIDIÓ "bpmn" (Diagrama de Proceso) ━━━
`pasos_as_is` es el proceso ACTUAL (con el problema descrito en el
Bloque 1) y `pasos_to_be` es el proceso PROPUESTO (con la solución del
Bloque 2/3) — ambos como secuencia ordenada de pasos {actor, accion,
tipo, usado_en_to_be}.
- `tipo` es uno de: "inicio", "fin", "tarea", "decision".
- `usado_en_to_be` (solo relevante dentro de `pasos_as_is`): marcá `false`
  en un paso del AS-IS cuando ese paso desaparece por completo en el
  rediseño TO-BE (ej. un paso manual/redundante que la solución elimina).
  Dejalo en `true` (default) para los pasos del AS-IS que se mantienen o
  se simplifican pero siguen existiendo. En `pasos_to_be` siempre va
  `true` — ahí no aplica el concepto de "paso eliminado".

━━━ SI SE PIDIÓ "bmc" (Business Model Canvas) ━━━
La entrevista ya indaga la mayoría de estos bloques de forma explícita —
usá ESA información real, no generalices si ya está en la conversación:
- segmentos_clientes: a partir del Bloque 1 (problema/alcance) — quién se
  ve afectado por el problema (qué departamentos, qué países).
- propuesta_valor: a partir del Bloque 2 (objetivo medible) y Bloque 3
  (beneficios) — qué cambia concretamente y qué se gana con la idea.
- canales: a partir de lo indagado en el Bloque 3 sobre cómo llega la
  solución a quien la usa.
- relaciones_clientes: a partir de lo indagado en el Bloque 3 sobre cómo
  se da soporte/comunicación a quien usa la idea.
- recursos_clave: a partir de lo indagado en el Bloque 4 sobre qué se
  necesita para construir/operar el entregable (personas, tecnología,
  herramientas).
- actividades_clave: a partir de lo indagado en el Bloque 4 sobre las
  tareas principales de implementación.
- socios_clave: a partir de lo indagado en el Bloque 1 sobre proveedores
  externos/terceros. Si la persona indicó explícitamente que no hay
  terceros involucrados, decilo así ("No se identificaron socios externos
  — la idea es de ejecución interna"), no lo dejes en blanco ni inventes uno.
- fuentes_ingreso: para ideas internas de mejora de proceso (el caso más
  común acá) normalmente NO hay ingreso nuevo, sino ahorro/eficiencia —
  redactalo en términos de ahorro de costos o tiempo (a partir del Bloque
  3), no fuerces un modelo de ingresos que no aplica a una idea interna.
- estructura_costos: redactalo a partir del RANGO DE PRESUPUESTO y el
  PLAZO DE ESFUERZO ya capturados en el Bloque 1 — NO preguntes ni
  inventes un desglose de costos más fino que ese, la política solo pide
  ese nivel de detalle.

━━━ SI SE PIDIÓ "raci" (Matriz de Responsabilidades) ━━━
Para cada actividad en `actividades`, el campo `asignaciones` es un STRING
con el formato exacto "Rol A: R; Rol B: A; Rol C: C" (rol, dos puntos,
letra; punto y coma entre pares). NUNCA lo dejes vacío ni pongas solo
"Pendiente" — es el error más común y hace que la tabla se genere sin
ninguna columna de rol, inutilizable.
- Los roles deben ser NOMBRES REALES derivados de la entrevista: el
  departamento del autor y los departamentos impactados (Bloque 1), el
  equipo o proveedor que construye el entregable (Bloque 4 y Socios Clave),
  y quien usa o se beneficia de la idea (ej. "Supervisor de Operaciones",
  "Equipo de TI", "Proveedor de telemática", "Finanzas") — no inventes
  roles genéricos tipo "Rol 1" si la conversación ya deja claro quién hace qué.
- Identificá entre 4 y 8 actividades concretas de implementación, a partir
  de los ENTREGABLES y ACTIVIDADES CLAVE indagados en el Bloque 4.
- Para cada actividad, incluí en `asignaciones` solo los roles que
  realmente participan de ESA actividad (2 a 4 roles típicamente, no hace
  falta repetir todos los roles en todas las actividades), cada uno con
  exactamente una letra: R (Responsable — quien ejecuta), A (Aprueba —
  quien autoriza, normalmente uno solo por actividad), C (Consultado — a
  quien se le pide opinión antes de actuar), I (Informado — a quien se le
  avisa del resultado). Ejemplo de un valor válido de `asignaciones`:
  "Equipo de TI: R; Supervisor de Operaciones: A; Choferes: I".

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
            # 16000 (no 8192, y muy por encima de generar_respuesta): esta
            # llamada genera el contenido narrativo completo de hasta 6
            # documentos a la vez — con un límite más bajo la respuesta se
            # corta a mitad de generarse y produce JSON inválido ("EOF while
            # parsing").
            #
            # 16000 es el techo práctico sin streaming: por encima de ~16K el
            # SDK arriesga timeout de HTTP y habría que pasar a
            # _client.messages.stream() + get_final_message().
            #
            # thinking deshabilitado: mismo fix que generar_respuesta — sin
            # esto el razonamiento adaptativo de Sonnet 5 compite por
            # presupuesto de tokens con el grammar del Structured Output y
            # puede cortar la respuesta a mitad de generarse.
            thinking={"type": "disabled"},
            max_tokens=16000,
            system=(
                f"Redacta el contenido para estos tipos de documento: {', '.join(tipos)}.\n\n"
                f"{_CRITERIOS_DOCUMENTOS}"
            ),
            messages=mensajes_anthropic,
            output_format=ContenidoDocumentosMultiple,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        # Fallo real de la API: documentos/generadores.py ya usa
        # `.get(clave) or "Pendiente de definir"` en cada campo, así que un
        # dict vacío por tipo es un fallback seguro — el .docx sale con
        # los campos narrativos marcados como pendientes, no rompe nada.
        logger.error("generar_contenido_documentos: fallo de API: %s", exc)
        return {tipo: {} for tipo in tipos}
    except Exception:
        # Red de seguridad — ver generar_respuesta.
        logger.exception("generar_contenido_documentos: excepción no prevista")
        return {tipo: {} for tipo in tipos}

    parsed = response.parsed_output
    if parsed is None:
        return {tipo: {} for tipo in tipos}

    resultado: dict[str, dict] = {}
    for tipo in tipos:
        sub_modelo = getattr(parsed, tipo, None)
        resultado[tipo] = sub_modelo.model_dump() if sub_modelo else {}

    if isinstance(parsed.raci, RaciContenido):
        # generadores.py y plantillas_html.py esperan roles/leyenda como
        # dict[str, str] (formato histórico) — se reconvierte acá desde el
        # string "Rol: Letra; Rol: Letra" que sí soporta el Structured
        # Output sin errores (ver docstring de ActividadRaci/LeyendaRaci).
        resultado["raci"]["actividades"] = [
            {
                "actividad": actividad.actividad,
                "roles": _parsear_asignaciones_raci(actividad.asignaciones),
            }
            for actividad in parsed.raci.actividades
        ]
        resultado["raci"]["leyenda"] = dict(_LEYENDA_RACI)

    return resultado


def _parsear_asignaciones_raci(asignaciones: str) -> dict[str, str]:
    """Convierte "Rol A: R; Rol B: A" -> {"Rol A": "R", "Rol B": "A"}.
    Ver docstring de ActividadRaci para por qué este campo es un string
    y no un dict[str,str] directo."""
    roles: dict[str, str] = {}
    for par in asignaciones.split(";"):
        if ":" not in par:
            continue
        rol, _, letra = par.partition(":")
        rol = rol.strip()
        letra = letra.strip().upper()
        if rol and letra:
            roles[rol] = letra
    return roles


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
            # 4096, no 1024 — ver generar_respuesta.
            thinking={"type": "disabled"},
            max_tokens=4096,
            system=_CRITERIOS_CLASIFICACION_BASE,
            messages=mensajes_anthropic,
            output_format=ClasificacionResultado,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.error("clasificar_idea: fallo de API: %s", exc)
        return None
    except Exception:
        # Red de seguridad — ver generar_respuesta.
        logger.exception("clasificar_idea: excepción no prevista")
        return None

    parsed = response.parsed_output
    if parsed is None:
        logger.error("clasificar_idea: la respuesta no se pudo parsear contra el schema esperado")
        return None

    return {"clasificacion": parsed.clasificacion, "justificacion": parsed.justificacion}


_CRITERIOS_ASIGNACION_REVISOR_DEFAULT = """
Analiza el CONTENIDO de esta idea (no el departamento de quien la escribió)
y decide a qué departamento de la lista dada le corresponde revisarla por
tema/materia.

Si se te da una sugerencia del autor sobre quién debería revisarla,
CONSIDÉRALA como una señal más, pero no la sigas ciegamente — evalúa si el
departamento que sugiere (o que se infiere de su sugerencia) realmente
coincide con el contenido de la idea. Puedes aceptarla o proponer otro
departamento con tu propia justificación.

Da una justificación breve y concreta, basada en el contenido real de la
entrevista.

IDIOMA: Siempre en español.
""".strip()


def asignar_revisor_ia(
    historial: list[dict],
    titulo: str,
    sugerencia_autor: str | None,
    motivo_autor: str | None,
    nombres_departamentos: list[str],
    criterio_texto: str,
) -> dict | None:
    """Sugiere a qué departamento le corresponde revisar una idea, a partir
    de su contenido real (no de la regla simple "mismo departamento del
    autor"). Devuelve None si la API falla o la respuesta no se puede
    parsear — el caller (revision/service.py) debe interpretar eso como
    "usa el fallback de mismo departamento del autor", nunca debe romper
    el envío de la idea.

    `criterio_texto` es el contenido activo de CriterioIA(tipo=asignacion_revisor)
    leído por el caller — antes este prompt era la constante hardcodeada
    _CRITERIOS_ASIGNACION_REVISOR_DEFAULT sin importar lo que un admin
    subiera en criterios/, un bug real (el criterio se guardaba pero nunca
    se usaba). El caller pasa ese default solo si todavía no existe
    ninguna fila activa en la BD.

    `acepto_sugerencia_autor` en el dict devuelto solo es significativo si
    `sugerencia_autor` no era None — el caller es responsable de forzarlo
    a None en BD cuando no hubo ninguna sugerencia que evaluar.
    """
    if settings.claude_stub_mode:
        return {
            "departamento": nombres_departamentos[0] if nombres_departamentos else None,
            "justificacion": "[STUB] asignación simulada",
            "acepto_sugerencia_autor": sugerencia_autor is not None,
        }

    if not nombres_departamentos:
        return None

    # Modelo Pydantic dinámico: el campo `departamento` queda restringido
    # (via Literal) a EXACTAMENTE los nombres de departamento recibidos,
    # igual que TipoCAB restringe `clasificacion` en clasificar_idea — así
    # la API garantiza estructuralmente que la IA no invente un
    # departamento que no existe.
    AsignacionRevisorResultado = create_model(
        "AsignacionRevisorResultado",
        departamento=(Literal[tuple(nombres_departamentos)], ...),
        justificacion=(str, ...),
        acepto_sugerencia_autor=(bool, ...),
    )

    transcripcion = "\n\n".join(
        f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
        for m in historial
    ) or "(sin mensajes de entrevista registrados)"

    bloque_sugerencia = (
        f"Sugerencia del autor sobre quién debería revisarla: {sugerencia_autor}\n"
        f"Motivo dado por el autor: {motivo_autor or '(sin motivo dado)'}\n\n"
        if sugerencia_autor
        else "El autor no dio ninguna sugerencia de revisor.\n\n"
    )

    mensajes_anthropic = [
        {
            "role": "user",
            "content": (
                f"Título de la idea: {titulo}\n\n"
                f"Departamentos disponibles: {', '.join(nombres_departamentos)}\n\n"
                f"{bloque_sugerencia}"
                f"Historial completo de la entrevista:\n\n{transcripcion}"
            ),
        }
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            # 4096, no 1024 — ver generar_respuesta.
            thinking={"type": "disabled"},
            max_tokens=4096,
            system=criterio_texto,
            messages=mensajes_anthropic,
            output_format=AsignacionRevisorResultado,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.error("asignar_revisor_ia: fallo de API: %s", exc)
        return None
    except Exception:
        # Red de seguridad — ver generar_respuesta.
        logger.exception("asignar_revisor_ia: excepción no prevista")
        return None

    parsed = response.parsed_output
    if parsed is None:
        logger.error("asignar_revisor_ia: la respuesta no se pudo parsear contra el schema esperado")
        return None

    return {
        "departamento": parsed.departamento,
        "justificacion": parsed.justificacion,
        "acepto_sugerencia_autor": parsed.acepto_sugerencia_autor,
    }


class AnalisisRiesgoResultado(BaseModel):
    probabilidad: int = Field(ge=1, le=5)
    impacto: int = Field(ge=1, le=5)
    justificacion: str


_CRITERIOS_ANALISIS_RIESGO = """
Analiza el riesgo de esta idea a partir del historial completo de su
entrevista, según la política de gestión de riesgo de ANC:

PROBABILIDAD (1-5): considera experiencia histórica con ideas similares,
dependencia de terceros, complejidad técnica/operativa, disponibilidad
del equipo necesario, madurez del proceso que se busca cambiar, y
supuestos no validados en la propuesta. 1 = muy poco probable que algo
salga mal, 5 = muy probable.

IMPACTO (1-5): considera el tiempo que tomaría o afectaría, el costo
involucrado, el alcance de lo que cambia, y qué tan crítica es el área
funcional afectada. 1 = impacto mínimo si algo sale mal, 5 = impacto
severo.

Da una justificación breve y concreta de ambos valores, basada en el
contenido real de la entrevista — no genérica.

IDIOMA: Siempre en español.
""".strip()


def analizar_riesgo_idea(historial: list[dict]) -> dict | None:
    """Calcula probabilidad e impacto (1-5 cada uno) para el análisis de
    riesgo automático de una idea. Es INFORMATIVO, no bloqueante: devuelve
    None ante cualquier fallo de la API o de parseo — el caller
    (riesgo/service.py) debe simplemente omitir la creación del análisis,
    nunca romper el flujo de creación de la revisión.

    nivel_riesgo (probabilidad × impacto) y categoria NUNCA se calculan
    acá — eso es responsabilidad del código en riesgo/service.py, no de
    la IA.
    """
    if settings.claude_stub_mode:
        return {"probabilidad": 3, "impacto": 3, "justificacion": "[STUB] análisis de riesgo simulado"}

    transcripcion = "\n\n".join(
        f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
        for m in historial
    ) or "(sin mensajes de entrevista registrados)"

    mensajes_anthropic = [
        {"role": "user", "content": f"Historial completo de la entrevista:\n\n{transcripcion}"}
    ]

    try:
        response = _client.messages.parse(
            model=settings.claude_model,
            # 4096, no 1024 — ver generar_respuesta.
            thinking={"type": "disabled"},
            max_tokens=4096,
            system=_CRITERIOS_ANALISIS_RIESGO,
            messages=mensajes_anthropic,
            output_format=AnalisisRiesgoResultado,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.error("analizar_riesgo_idea: fallo de API: %s", exc)
        return None
    except Exception:
        # Red de seguridad — ver generar_respuesta.
        logger.exception("analizar_riesgo_idea: excepción no prevista")
        return None

    parsed = response.parsed_output
    if parsed is None:
        logger.error("analizar_riesgo_idea: la respuesta no se pudo parsear contra el schema esperado")
        return None

    return {
        "probabilidad": parsed.probabilidad,
        "impacto": parsed.impacto,
        "justificacion": parsed.justificacion,
    }


def responder_pregunta_idea(historial: list[dict], pregunta: str) -> str:
    """Responde una pregunta puntual de quien revisa/aprueba una idea
    (revisor de área o miembro del CAB), a partir del historial completo
    de la entrevista. Es una consulta EFÍMERA — no se persiste en ningún
    lado, ver ideas/router.py:preguntar.

    Texto plano (no Structured Output): a diferencia de clasificar_idea o
    asignar_revisor_ia, acá no hay ningún campo que el backend necesite
    extraer o validar para actuar — la respuesta se muestra tal cual en
    el mini-chat del frontend, así que forzar un schema no aporta nada.
    """
    if settings.claude_stub_mode:
        return f"[STUB] Respuesta simulada a: {pregunta}"

    transcripcion = "\n\n".join(
        f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
        for m in historial
    ) or "(sin mensajes de entrevista registrados)"

    try:
        response = _client.messages.create(
            model=settings.claude_model,
            # 4096, no 1024 — ver generar_respuesta. Acá además la respuesta
            # es texto libre que se muestra tal cual en el mini-chat, así que
            # un corte por presupuesto se ve como una frase a medias.
            thinking={"type": "disabled"},
            max_tokens=4096,
            system=(
                "Eres un asistente que ayuda a quien revisa o aprueba una idea a "
                "entenderla mejor, respondiendo preguntas puntuales sobre su contenido "
                "a partir del historial completo de la entrevista. Responde de forma "
                "breve y concreta, basándote únicamente en lo que dice la conversación "
                "— si algo no se mencionó, dilo explícitamente en vez de inventar.\n\n"
                "IDIOMA: Siempre en español."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Historial completo de la entrevista:\n\n{transcripcion}\n\nPregunta: {pregunta}",
                }
            ],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.error("responder_pregunta_idea: fallo de API: %s", exc)
        return "No se pudo procesar la pregunta en este momento. Intenta de nuevo."
    except Exception:
        # Red de seguridad: sin esto, una excepción no prevista (ej. timeout
        # de red hacia Anthropic, más probable en conexiones remotas/lentas)
        # se propagaba sin atrapar hasta ideas/router.py:preguntar, y de ahí
        # a un 500 fuera del stack de CORSMiddleware — el navegador lo
        # reportaba como "blocked by CORS policy" en vez de como el fallo
        # real que era.
        logger.exception("responder_pregunta_idea: excepción no prevista")
        return "No se pudo procesar la pregunta en este momento. Intenta de nuevo."

    # BUG REAL encontrado en diagnóstico: `response.content[0].text` asumía
    # que el primer bloque siempre es texto, pero con razonamiento adaptativo
    # activo el primer bloque era SIEMPRE un ThinkingBlock, no un TextBlock —
    # `.text` no existe ahí y esto rompía el endpoint el 100% de las veces
    # (no intermitente), con el mismo síntoma de "CORS bloqueado" que el
    # except Exception de arriba atrapa. El fix real fue buscar el primer
    # bloque de tipo "text" en vez de asumir la posición 0.
    #
    # Con `thinking: disabled` (ver más abajo) ya no debería aparecer ningún
    # ThinkingBlock, pero este loop se deja como defensa — no tiene costo y
    # cubre un cambio de comportamiento futuro del SDK/modelo.
    for bloque in response.content:
        if bloque.type == "text":
            return bloque.text

    logger.error("responder_pregunta_idea: la respuesta no tuvo ningún bloque de texto")
    return "No se pudo procesar la pregunta en este momento. Intenta de nuevo."


def generar_resumen_idea(historial: list[dict]) -> str | None:
    """Genera un resumen real (problema + propuesta + beneficio) de una idea
    a partir del transcript completo de su entrevista, para quien la revisa
    (ideas/router.py:obtener_resumen). Antes de esto, ese endpoint devolvía
    el último mensaje del asistente tal cual.

    Devuelve None ante cualquier fallo de la API o de parseo — el caller
    (ideas/router.py:obtener_resumen) debe interpretar eso como "usa el
    fallback del último intercambio de la entrevista", nunca debe romper la
    vista de revisión ni mostrar un mensaje de error crudo donde antes había
    contenido (mismo criterio que asignar_revisor_ia/analizar_riesgo_idea).

    Mismo formato de entrada que responder_pregunta_idea: [{"role": ...,
    "content": ...}] con role "asistente"/"usuario".
    """
    if settings.claude_stub_mode:
        return "[STUB] Resumen simulado de la idea."

    transcripcion = "\n\n".join(
        f"{'Asistente' if m['role'] == 'asistente' else 'Usuario'}: {m['content']}"
        for m in historial
    ) or "(sin mensajes de entrevista registrados)"

    try:
        response = _client.messages.create(
            model=settings.claude_model,
            thinking={"type": "disabled"},
            max_tokens=1024,
            system=(
                "Eres un asistente que resume ideas de mejora para quien las revisa o "
                "aprueba. A partir del historial completo de una entrevista, redacta un "
                "resumen de 2 a 3 líneas que cubra: el problema identificado, la "
                "propuesta/solución planteada, y el beneficio esperado.\n\n"
                "Basate ÚNICAMENTE en lo que dice la conversación — si algo no se "
                "mencionó (ej. no hay beneficio claro todavía), decilo explícitamente "
                "en vez de inventarlo.\n\n"
                "IDIOMA: Siempre en español."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Historial completo de la entrevista:\n\n{transcripcion}",
                }
            ],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.error("generar_resumen_idea: fallo de API: %s", exc)
        return None
    except Exception:
        # Red de seguridad — ver generar_respuesta.
        logger.exception("generar_resumen_idea: excepción no prevista")
        return None

    # Mismo cuidado que responder_pregunta_idea: sin `thinking: disabled` el
    # primer bloque podía ser un ThinkingBlock, no texto — se deja este loop
    # como defensa aunque ya no debería aparecer ninguno.
    for bloque in response.content:
        if bloque.type == "text":
            return bloque.text

    logger.error("generar_resumen_idea: la respuesta no tuvo ningún bloque de texto")
    return None


TURNOS_USUARIO_PARA_COMPLETAR_STUB = 3


_ORDEN_BLOQUES_STUB = ["problema_alcance", "objetivo_medible", "beneficios", "entregables", "riesgos"]


def _progreso_bloques_stub(turnos_usuario: int) -> dict:
    """Simula avance incremental: 1 bloque completado por turno de usuario,
    proporcional a TURNOS_USUARIO_PARA_COMPLETAR_STUB, para poder probar el
    checklist en frontend sin depender de la API real."""
    completados = int(len(_ORDEN_BLOQUES_STUB) * min(turnos_usuario, TURNOS_USUARIO_PARA_COMPLETAR_STUB) / TURNOS_USUARIO_PARA_COMPLETAR_STUB)
    progreso = {}
    for i, clave in enumerate(_ORDEN_BLOQUES_STUB):
        if i < completados:
            progreso[clave] = EstadoBloque.completado.value
        elif i == completados and turnos_usuario > 0:
            progreso[clave] = EstadoBloque.en_progreso.value
        else:
            progreso[clave] = EstadoBloque.pendiente.value
    return progreso


def _respuesta_stub(mensajes: list[dict], system_prompt: str) -> dict:
    turnos_usuario = sum(1 for m in mensajes if m.get("role") == "usuario")
    bloques_completos = turnos_usuario >= TURNOS_USUARIO_PARA_COMPLETAR_STUB

    # entrevista_completa SIEMPRE False — ver REGLA DE CIERRE en
    # _CRITERIOS_ENTREVISTA: el envío ya no lo dispara la IA, lo dispara
    # el botón "Enviar idea" (POST /ideas/{id}/enviar) una vez que
    # progreso_bloques muestra los 5 bloques "completado".
    # Se alternan turnos con y sin `options` para poder probar en el
    # navegador tanto los botones de respuesta rápida como el campo de
    # texto libre, sin depender de la API real.
    opciones = None

    if bloques_completos:
        mensaje = (
            "[STUB] ¡Listo, ya tengo todo lo que necesitaba! ¿Querés agregar algo más, "
            "o lo mandamos ya con el botón 'Enviar idea'?"
        )
        progreso_bloques = dict(_PROGRESO_BLOQUES_COMPLETO)
    else:
        mensaje = (
            "[STUB] Respuesta simulada — contame un poquito más "
            f"(turno {turnos_usuario} de {TURNOS_USUARIO_PARA_COMPLETAR_STUB})."
        )
        progreso_bloques = _progreso_bloques_stub(turnos_usuario)
        if turnos_usuario % 2 == 1:
            opciones = [
                # Copia literal de las 5 opciones del prompt real
                # (_CRITERIOS_ENTREVISTA) — si cambian allá, cambian acá.
                "Nada — lo haríamos con personal ANC",
                "Hasta $10,000",
                "Entre $10,000 y $20,000",
                "Entre $20,000 y $30,000",
                "Más de $30,000",
            ]

    return {
        "message": mensaje,
        "entrevista_completa": False,
        "options": opciones,
        "progreso_bloques": progreso_bloques,
        "raw": None,
        # El stub simula una respuesta exitosa, no un fallo: no es degradado.
        "degradado": False,
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
