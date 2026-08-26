"""Deriva el estado "de flujo" (Flow Control) de cada idea a partir de la
cascada de 5 tablas (ideas -> revision -> clasificacion -> comites ->
documentos) — mismo patrón de lectura que ideas/service.py:construir_linea_tiempo,
pero para TODAS las ideas a la vez, devolviendo el estado ACTUAL (no un
timeline de eventos históricos).

Cada fila de una tabla más adelante en la cascada solo existe si la
anterior llegó a su estado de aprobación (ver docstrings de
crear_revision_para_idea / crear_clasificacion_para_idea /
crear_comite_idea_para_idea) — por eso alcanza con mirar, en orden, cuál es
la tabla más avanzada que existe para cada idea.

LIMITACIÓN CONOCIDA (aceptada, no se resuelve acá): si una idea rechazada
por comité se reclasifica, comites/service.py:crear_comite_idea_para_idea
reabre la MISMA fila de ComiteIdea (resetea estado/motivo_rechazo/etc.)
pero NO resetea `creado_en` — la antigüedad en "comite_en_cola" tras una
reapertura se calcula desde la primera vez que entró a cola, no desde la
reapertura. Caso borde infrecuente, confirmado con el usuario que se deja
así por ahora.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.models import ComiteIdea, EstadoComite
from comites.service import departamentos_visibles, idea_departamento_visible
from documentos.models import DocumentoGenerado, TipoDocumento
from ideas.models import Idea
from revision.models import EstadoRevision, HistorialRetroalimentacion, RevisionIdea
from usuarios.models import MiembroCAB, Usuario

logger = logging.getLogger("uvicorn.error")

TOTAL_TIPOS_DOCUMENTO = len(TipoDocumento)

# Orden canónico de las 10 etapas — el frontend lo usa tal cual para las
# columnas de la matriz y los nodos del pipeline (ver
# frontend/src/trazabilidad/estadosFlow.ts).
ESTADOS_FLOW: list[str] = [
    "borrador",
    "revision_pendiente_asignacion",
    "revision_en_curso",
    "revision_cambios_solicitados",
    "revision_rechazada",
    "clasificacion_pendiente",
    "comite_en_cola",
    "comite_rechazada",
    "comite_aprobada_sin_documentos",
    "documentos_en_generacion",
    "documentos_completos",
]


def _persona_resumen(usuario: Usuario | None) -> dict | None:
    if usuario is None:
        return None
    return {"id": usuario.id, "nombre": usuario.nombre}


def _derivar_estado(
    idea: Idea,
    revision: RevisionIdea | None,
    clasificacion: ClasificacionIdea | None,
    comite: ComiteIdea | None,
    documentos: list[DocumentoGenerado],
    ultima_retro_por_revision: dict[int, HistorialRetroalimentacion],
) -> tuple[str, datetime]:
    if revision is None:
        return "borrador", idea.fecha_creacion

    if revision.estado == EstadoRevision.pendiente_asignacion:
        return "revision_pendiente_asignacion", revision.creado_en

    if revision.estado == EstadoRevision.pendiente_revision:
        return "revision_en_curso", revision.fecha_asignacion or revision.creado_en

    if revision.estado == EstadoRevision.pendiente_aceptacion_reasignacion:
        # Se COLAPSA a "en curso" a propósito: para el autor la idea sigue en
        # revisión: que dos personas estén resolviendo quién la atiende es
        # negociación interna que no cambia en qué etapa está ni qué se espera
        # de él. Antes caía acá por descarte (la rama de "aprobada"), que daba
        # el mismo resultado por casualidad, no por decisión.
        return "revision_en_curso", revision.fecha_asignacion or revision.creado_en

    if revision.estado == EstadoRevision.cambios_solicitados:
        ultima_retro = ultima_retro_por_revision.get(revision.id)
        fecha = ultima_retro.creada_en if ultima_retro else (revision.fecha_resolucion or revision.creado_en)
        return "revision_cambios_solicitados", fecha

    if revision.estado == EstadoRevision.rechazada:
        # Terminal: el rechazo del encargado de área es final, no se reabre ni
        # se reasigna (ver revision/models.py:EstadoRevision.rechazada) y la
        # idea nunca llega a ClasificacionIdea ni a ComiteIdea.
        #
        # Antes NO existía esta rama: `rechazada` caía en la de "aprobada", no
        # encontraba clasificación y salía por el fallback defensivo como
        # "revision_en_curso". Una idea rechazada se mostraba "En revisión"
        # para siempre, y ESTADOS_FLOW ni siquiera tenía un valor para esto.
        return "revision_rechazada", revision.fecha_resolucion or revision.creado_en

    if revision.estado != EstadoRevision.aprobada:
        # No es un caso de datos inconsistentes: es un valor del enum que este
        # código no contempla. Se rompe fuerte a propósito — los dos bugs que
        # motivaron este cambio se colaron justamente porque una rama "todo lo
        # demás es aprobada" los absorbió en silencio.
        raise ValueError(
            f"EstadoRevision no contemplado en _derivar_estado: {revision.estado!r}. "
            "Agregá la rama explícita y su valor en ESTADOS_FLOW (y en el "
            "EstadoFlow del frontend) antes de usar el estado nuevo."
        )

    # revision.estado == aprobada a partir de acá.
    if clasificacion is None:
        # Datos inconsistentes, NO un hueco del enum: ClasificacionIdea se crea
        # atómicamente al aprobar (revision/router.py:aprobar). Acá sí se
        # degrada en vez de romper —una fila rara no puede tumbar el listado de
        # todas las ideas— pero se loguea para que no pase inadvertido.
        logger.warning(
            "Idea %s tiene la revisión aprobada pero no existe ClasificacionIdea; "
            "se reporta como revision_en_curso",
            idea.id,
        )
        return "revision_en_curso", revision.fecha_asignacion or revision.creado_en

    if clasificacion.estado == EstadoClasificacion.pendiente_clasificacion:
        return "clasificacion_pendiente", clasificacion.creado_en

    # clasificacion.estado == clasificada a partir de acá.
    if comite is None:
        # Datos inconsistentes, mismo criterio que el caso de clasificación:
        # ComiteIdea se crea atómicamente al clasificar
        # (clasificacion/router.py:clasificar).
        logger.warning(
            "Idea %s está clasificada pero no existe ComiteIdea; "
            "se reporta como clasificacion_pendiente",
            idea.id,
        )
        return "clasificacion_pendiente", clasificacion.creado_en

    if comite.estado == EstadoComite.pendiente:
        return "comite_en_cola", comite.creado_en

    if comite.estado == EstadoComite.pendiente_aceptacion_reasignacion:
        # Se COLAPSA a "en cola", mismo criterio que en revisión.
        #
        # Este era el bug más grave de los dos: antes caía en la rama de
        # "aprobada" y la idea se reportaba como comite_aprobada_sin_documentos
        # — o sea que al autor se le mostraba su idea APROBADA por el comité
        # cuando en realidad nadie había decidido nada, solo se estaba
        # negociando quién la atiende.
        return "comite_en_cola", comite.creado_en

    if comite.estado == EstadoComite.rechazada:
        return "comite_rechazada", comite.fecha_resolucion or comite.creado_en

    if comite.estado != EstadoComite.aprobada:
        # Mismo criterio que en revisión: hueco del enum, se rompe fuerte.
        raise ValueError(
            f"EstadoComite no contemplado en _derivar_estado: {comite.estado!r}. "
            "Agregá la rama explícita y su valor en ESTADOS_FLOW (y en el "
            "EstadoFlow del frontend) antes de usar el estado nuevo."
        )

    # comite.estado == aprobada a partir de acá.
    tipos_generados = {d.tipo_documento for d in documentos}
    if not tipos_generados:
        return "comite_aprobada_sin_documentos", comite.fecha_resolucion or comite.creado_en
    if len(tipos_generados) < TOTAL_TIPOS_DOCUMENTO:
        return "documentos_en_generacion", min(d.generado_en for d in documentos)
    return "documentos_completos", max(d.generado_en for d in documentos)


def estados_flow_por_idea(db: Session, ideas: list[Idea]) -> dict[int, str]:
    """{idea_id: estado_flow} para un conjunto acotado de ideas.

    Existe para que GET /ideas pueda pintar el estado real del flujo en la
    lista de "Mis ideas" (Idea.estado solo distingue borrador/enviada, así que
    el badge decía "enviada" desde el envío hasta la aprobación del comité).

    EN BLOQUE, no por idea: son 5 queries fijas filtradas por los idea_id
    pedidos, no 5 por cada idea. Hacerlo con un `_derivar_estado` por fila
    habría metido un N+1 en el endpoint que más se llama de la app.

    No reusa construir_flow_control porque ese carga TODAS las ideas del
    sistema y resuelve además autores, revisores y miembros de CAB — para un
    badge alcanza el estado, y un colaborador solo pide las suyas.
    """
    if not ideas:
        return {}

    ids = [idea.id for idea in ideas]

    revisiones = {r.idea_id: r for r in db.query(RevisionIdea).filter(RevisionIdea.idea_id.in_(ids)).all()}
    clasificaciones = {
        c.idea_id: c for c in db.query(ClasificacionIdea).filter(ClasificacionIdea.idea_id.in_(ids)).all()
    }
    comites = {c.idea_id: c for c in db.query(ComiteIdea).filter(ComiteIdea.idea_id.in_(ids)).all()}

    documentos_por_idea: dict[int, list[DocumentoGenerado]] = defaultdict(list)
    for doc in db.query(DocumentoGenerado).filter(DocumentoGenerado.idea_id.in_(ids)).all():
        documentos_por_idea[doc.idea_id].append(doc)

    ultima_retro_por_revision: dict[int, HistorialRetroalimentacion] = {}
    revision_ids = [r.id for r in revisiones.values()]
    if revision_ids:
        for h in (
            db.query(HistorialRetroalimentacion)
            .filter(HistorialRetroalimentacion.revision_id.in_(revision_ids))
            .order_by(HistorialRetroalimentacion.creada_en)
            .all()
        ):
            ultima_retro_por_revision[h.revision_id] = h

    resultado: dict[int, str] = {}
    for idea in ideas:
        estado_flow, _fecha = _derivar_estado(
            idea,
            revisiones.get(idea.id),
            clasificaciones.get(idea.id),
            comites.get(idea.id),
            documentos_por_idea.get(idea.id, []),
            ultima_retro_por_revision,
        )
        resultado[idea.id] = estado_flow
    return resultado


def construir_flow_control(db: Session) -> list[dict]:
    ideas = db.query(Idea).options(joinedload(Idea.autor)).all()

    revisiones = {
        r.idea_id: r for r in db.query(RevisionIdea).options(joinedload(RevisionIdea.revisor)).all()
    }
    clasificaciones = {c.idea_id: c for c in db.query(ClasificacionIdea).all()}
    comites = {c.idea_id: c for c in db.query(ComiteIdea).all()}

    documentos_por_idea: dict[int, list[DocumentoGenerado]] = defaultdict(list)
    for doc in db.query(DocumentoGenerado).all():
        documentos_por_idea[doc.idea_id].append(doc)

    # Última retroalimentación por revision_id — ancla append-only de "cuándo
    # entró a cambios_solicitados", a diferencia de RevisionIdea.fecha_resolucion
    # que se sobrescribe en cada ciclo aprobar/pedir-cambios.
    ultima_retro_por_revision: dict[int, HistorialRetroalimentacion] = {}
    for h in db.query(HistorialRetroalimentacion).order_by(HistorialRetroalimentacion.creada_en).all():
        ultima_retro_por_revision[h.revision_id] = h

    # Ya NO por tipo_cab (metadata pura desde CAB-por-departamento, ver
    # usuarios/models.py:MiembroCAB) — mismo criterio real que
    # comites/router.py:cola_comite: departamentos_visibles() por cada
    # miembro de CAB, resuelto una sola vez acá para no repetir la query
    # por cada idea.
    miembros_cab_con_departamentos: list[tuple[Usuario, list[int] | None]] = [
        (miembro.usuario, departamentos_visibles(db, miembro.usuario))
        for miembro in db.query(MiembroCAB).options(joinedload(MiembroCAB.usuario)).all()
    ]

    ahora = datetime.now(timezone.utc)
    filas: list[dict] = []

    for idea in ideas:
        revision = revisiones.get(idea.id)
        clasificacion = clasificaciones.get(idea.id)
        comite = comites.get(idea.id)
        documentos = documentos_por_idea.get(idea.id, [])

        estado_flow, fecha_entrada = _derivar_estado(
            idea, revision, clasificacion, comite, documentos, ultima_retro_por_revision
        )

        miembros_comite = None
        if comite is not None:
            departamento_autor = idea.autor.departamento_id if idea.autor else None
            miembros_comite = [
                _persona_resumen(usuario)
                for usuario, departamentos in miembros_cab_con_departamentos
                if idea_departamento_visible(departamento_autor, departamentos)
            ]

        dias_en_etapa = max(0, (ahora - fecha_entrada).days)

        filas.append(
            {
                "idea_id": idea.id,
                "titulo": idea.titulo,
                "estado_flow": estado_flow,
                "departamento_id": idea.autor.departamento_id if idea.autor else None,
                "departamento_nombre": None,  # lo completa el router con el catálogo de departamentos
                "autor": _persona_resumen(idea.autor),
                "revisor": _persona_resumen(revision.revisor) if revision else None,
                "miembros_comite": miembros_comite,
                "fecha_entrada_etapa": fecha_entrada,
                "dias_en_etapa": dias_en_etapa,
            }
        )

    return filas
