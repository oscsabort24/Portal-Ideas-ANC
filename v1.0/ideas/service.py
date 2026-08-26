from sqlalchemy import func
from sqlalchemy.orm import Session

from ideas.models import Idea, MensajeEntrevista


def siguiente_orden(db: Session, idea_id: int) -> int:
    maximo = db.query(func.max(MensajeEntrevista.orden)).filter(
        MensajeEntrevista.idea_id == idea_id
    ).scalar()
    return (maximo or 0) + 1


def historial_para_ia(db: Session, idea_id: int) -> list[dict]:
    """Transcript de la entrevista en el formato que espera core/claude_client.

    ÚNICO punto de entrada para armar el historial que se le manda al modelo.
    Antes esta query estaba repetida en siete lugares —cuatro inline en
    ideas/router.py y tres copias idénticas de `_historial_para_ia` en
    clasificacion/, documentos/ y revision/— y ninguna filtraba los mensajes
    degradados, así que un fallo técnico del backend volvía al modelo como si
    fuera un turno propio del asistente. Eso contaminaba no solo la
    entrevista sino el resumen que leen los revisores y el contenido de los
    seis documentos formales que llegan al CAB.

    Centralizarlo es parte del fix: cualquier consumidor futuro hereda el
    filtro sin tener que acordarse.

    OJO — hay dos lugares que consultan mensajes_entrevista y que NO deben
    usar esta función, porque necesitan ver los mensajes tal como están
    guardados:
      - La búsqueda de idempotencia (ideas/router.py:enviar_mensaje): tiene
        que encontrar el turno realmente persistido, degradado incluido. Si
        se filtrara, un reintento no lo vería, crearía un turno nuevo y
        violaría el índice único de idempotency_key.
      - GET /ideas/{id}: devuelve el historial para pintar el chat, y la
        persona debe seguir viendo su conversación completa.
    """
    mensajes = (
        db.query(MensajeEntrevista)
        .filter(
            MensajeEntrevista.idea_id == idea_id,
            # `== False` y no `.is_(False)`: SQL Server solo admite IS con
            # NULL, así que .is_(False) genera "degradado IS 0" y revienta
            # con "Incorrect syntax near '0'". Con `== False` sale
            # "degradado = 0", que es lo correcto — y la columna es NOT NULL,
            # así que no hay un tercer estado que se pueda escapar.
            MensajeEntrevista.degradado == False,  # noqa: E712
        )
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    return [{"role": m.rol.value, "content": m.contenido} for m in mensajes]


def construir_linea_tiempo(db: Session, idea: Idea) -> list[dict]:
    """Ensambla el timeline de una idea leyendo las tablas existentes de
    ideas/, revision/, clasificacion/, comites/ y documentos/ — no hay
    ningún modelo propio de "eventos", se computa en cada lectura.

    Ver revision/models.py:HistorialReasignacion — los reasignos previos
    a la existencia de esa tabla no aparecen aquí (dato ya perdido).
    """
    # Imports diferidos para evitar un ciclo a nivel de módulo: estos
    # módulos (revision/clasificacion/comites/documentos) importan
    # ideas.models, así que ideas.service no puede importarlos a nivel
    # de módulo sin arriesgar un ciclo si algún día ellos importan
    # ideas.service también.
    from clasificacion.models import ClasificacionIdea
    from comites.models import ComiteIdea, EstadoComite
    from documentos.models import DocumentoGenerado
    from revision.models import EstadoRevision, HistorialReasignacion, HistorialRetroalimentacion, RevisionIdea
    from usuarios.models import TipoCAB

    eventos: list[dict] = []

    if idea.fecha_envio:
        eventos.append({
            "tipo": "idea_enviada",
            "descripcion": "Idea enviada",
            "fecha": idea.fecha_envio,
            "color": "info",
        })

    revision = db.query(RevisionIdea).filter_by(idea_id=idea.id).first()
    if revision:
        if revision.revisor_id is None:
            eventos.append({
                "tipo": "revision_pendiente_asignacion",
                "descripcion": "Pendiente de asignación",
                "fecha": revision.creado_en,
                "color": "advertencia",
            })
        elif revision.fecha_asignacion:
            eventos.append({
                "tipo": "revision_asignada",
                "descripcion": f"Asignada automáticamente a {revision.revisor.nombre}",
                "fecha": revision.fecha_asignacion,
                "color": "info",
            })

        reasignaciones = (
            db.query(HistorialReasignacion)
            .filter_by(revision_id=revision.id)
            .order_by(HistorialReasignacion.creada_en)
            .all()
        )
        for r in reasignaciones:
            eventos.append({
                "tipo": "revision_reasignada",
                "descripcion": f"Reasignada de {r.revisor_anterior.nombre} a {r.revisor_nuevo.nombre}",
                "fecha": r.creada_en,
                "color": "info",
            })

        historial_retro = (
            db.query(HistorialRetroalimentacion)
            .filter_by(revision_id=revision.id)
            .order_by(HistorialRetroalimentacion.creada_en)
            .all()
        )
        for h in historial_retro:
            eventos.append({
                "tipo": "revision_cambios_solicitados",
                "descripcion": f'Cambios solicitados: "{h.retroalimentacion}"',
                "fecha": h.creada_en,
                "color": "advertencia",
            })

        if revision.estado == EstadoRevision.aprobada and revision.fecha_resolucion:
            eventos.append({
                "tipo": "revision_aprobada",
                "descripcion": f"Aprobada en revisión (por {revision.revisor.nombre})",
                "fecha": revision.fecha_resolucion,
                "color": "exito",
            })
        elif revision.estado == EstadoRevision.rechazada and revision.fecha_resolucion:
            eventos.append({
                "tipo": "revision_rechazada",
                "descripcion": f'Rechazada por el revisor de área ({revision.revisor.nombre}): "{revision.motivo_rechazo}"',
                "fecha": revision.fecha_resolucion,
                "color": "peligro",
            })

    clasificacion = db.query(ClasificacionIdea).filter_by(idea_id=idea.id).first()
    if clasificacion and clasificacion.clasificacion and clasificacion.fecha_clasificacion:
        etiqueta = "Innovación" if clasificacion.clasificacion == TipoCAB.innovacion else "Transformación Digital"
        # clasificado_por_id=None es el caso NORMAL (clasificación automática
        # por IA, ver clasificacion/service.py) — no un dato faltante. Solo
        # queda con un usuario real cuando un admin la reclasifica a mano
        # (clasificacion/router.py:61).
        clasificador = clasificacion.clasificado_por.nombre if clasificacion.clasificado_por else "IA"
        eventos.append({
            "tipo": "clasificacion",
            "descripcion": f"Clasificada como {etiqueta} (por {clasificador})",
            "fecha": clasificacion.fecha_clasificacion,
            "color": "info",
        })

    comite = db.query(ComiteIdea).filter_by(idea_id=idea.id).first()
    if comite and comite.fecha_resolucion:
        if comite.estado == EstadoComite.aprobada:
            eventos.append({
                "tipo": "comite_aprobado",
                "descripcion": f"Aprobada por el CAB (por {comite.aprobada_o_rechazada_por.nombre})",
                "fecha": comite.fecha_resolucion,
                "color": "exito",
            })
        elif comite.estado == EstadoComite.rechazada:
            eventos.append({
                "tipo": "comite_rechazado",
                "descripcion": f'Rechazada por el CAB: "{comite.motivo_rechazo}"',
                "fecha": comite.fecha_resolucion,
                "color": "peligro",
            })

    primer_documento = (
        db.query(DocumentoGenerado)
        .filter_by(idea_id=idea.id)
        .order_by(DocumentoGenerado.generado_en)
        .first()
    )
    if primer_documento:
        eventos.append({
            "tipo": "documentos_generados",
            "descripcion": "Documentos generados",
            "fecha": primer_documento.generado_en,
            "color": "exito",
        })

    eventos.sort(key=lambda e: e["fecha"])
    return eventos
