from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from clasificacion.service import crear_clasificacion_para_idea
from core.database import get_db
from core.reasignacion import obtener_bloqueado_para_reasignar
from ideas.models import HistorialIdea, MensajeEntrevista, RolMensaje, TipoEventoIdea
from ideas.service import siguiente_orden
from permisos.models import ClavePermiso
from permisos.service import rol_tiene_permiso
from revision import schemas
from revision.models import EstadoRevision, HistorialRetroalimentacion, OrigenAsignacion, RevisionIdea
from revision.service import aplicar_rechazo_reasignacion, expirar_reasignaciones_vencidas
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual, requerir_admin

router = APIRouter(prefix="/revision", tags=["revision"])


def _validar_revisor_destino(db: Session, revisor_id: int) -> usuarios_models.Usuario:
    revisor = db.get(usuarios_models.Usuario, revisor_id)
    if not revisor:
        raise HTTPException(status_code=404, detail="El usuario destino no existe")
    if not rol_tiene_permiso(db, revisor.rol, ClavePermiso.es_revisor_elegible):
        raise HTTPException(
            status_code=400,
            detail=f"'{revisor.nombre}' no tiene un rol habilitado para revisar",
        )
    if not revisor.activo:
        raise HTTPException(status_code=400, detail=f"'{revisor.nombre}' no puede ser revisor: está inactivo")
    return revisor


@router.get("/mias", response_model=list[schemas.RevisionDetalleOut])
def mis_revisiones(
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    # Mismo patrón de "admin ve todo" que GET /ideas: un admin ve TODAS las
    # revisiones pendientes (no solo las suyas), para poder actuar sobre
    # cualquiera vía el atajo de admin en _validar_revisor_asignado.
    #
    # Se incluyen dos cosas distintas en la misma lista:
    #   - lo que ya es tuyo (pendiente_revision, revisor_id = vos)
    #   - lo que te PROPUSIERON (pendiente_aceptacion_reasignacion,
    #     propuesto_a_id = vos), que requiere que aceptes o rechaces antes
    #     de poder trabajarla.
    # El frontend las distingue por `estado` y marca las segundas con el
    # badge de "requiere tu respuesta" (no hay correo: notificaciones/ tiene
    # el envío en stub, sin credenciales SMTP).
    #
    # Una revisión propuesta a otra persona sigue apareciéndole a su revisor
    # actual, porque hasta la aceptación la responsabilidad no se movió.
    estados_visibles = (EstadoRevision.pendiente_revision, EstadoRevision.pendiente_aceptacion_reasignacion)
    query = db.query(RevisionIdea).filter(RevisionIdea.estado.in_(estados_visibles))
    if usuario_actual.rol != usuarios_models.RolUsuario.admin:
        query = query.filter(
            or_(
                RevisionIdea.revisor_id == usuario_actual.id,
                RevisionIdea.propuesto_a_id == usuario_actual.id,
            )
        )
    return query.all()


@router.get("/sin-asignar", response_model=list[schemas.RevisionDetalleOut])
def revisiones_sin_asignar(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    return db.query(RevisionIdea).filter(RevisionIdea.estado == EstadoRevision.pendiente_asignacion).all()


def _obtener_revision(db: Session, idea_id: int) -> RevisionIdea:
    revision = db.query(RevisionIdea).filter_by(idea_id=idea_id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="No existe revisión para esta idea")
    return revision


@router.post("/{idea_id}/asignar", response_model=schemas.RevisionOut)
def asignar(
    idea_id: int,
    payload: schemas.AsignarRequest,
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    revision = _obtener_revision(db, idea_id)
    if revision.estado != EstadoRevision.pendiente_asignacion:
        raise HTTPException(status_code=400, detail="Esta idea no está pendiente de asignación")

    revisor = _validar_revisor_destino(db, payload.revisor_id)

    revision.revisor_id = revisor.id
    revision.estado = EstadoRevision.pendiente_revision
    revision.fecha_asignacion = datetime.now(timezone.utc)
    revision.origen_asignacion = OrigenAsignacion.manual
    # Sale del pool tras el doble rechazo: la racha se corta acá.
    revision.rechazos_reasignacion_consecutivos = 0
    db.commit()
    db.refresh(revision)
    return revision


def _validar_revisor_asignado(revision: RevisionIdea, usuario_actual: usuarios_models.Usuario) -> None:
    # Atajo de admin: mismo patrón que comites/router.py:_validar_acceso_comite_idea.
    if usuario_actual.rol == usuarios_models.RolUsuario.admin:
        return
    if revision.revisor_id != usuario_actual.id:
        raise HTTPException(status_code=403, detail="No eres el revisor asignado a esta idea")


@router.post("/{idea_id}/aprobar", response_model=schemas.RevisionOut)
def aprobar(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    revision = _obtener_revision(db, idea_id)
    _validar_revisor_asignado(revision, usuario_actual)
    if revision.estado != EstadoRevision.pendiente_revision:
        raise HTTPException(status_code=400, detail="Esta idea ya no está pendiente de revisión")

    revision.estado = EstadoRevision.aprobada
    revision.fecha_resolucion = datetime.now(timezone.utc)
    crear_clasificacion_para_idea(db, revision.idea)
    db.commit()
    db.refresh(revision)
    return revision


@router.post("/{idea_id}/pedir-cambios", response_model=schemas.RevisionOut)
def pedir_cambios(
    idea_id: int,
    payload: schemas.PedirCambiosRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    if not payload.retroalimentacion.strip():
        raise HTTPException(status_code=400, detail="La retroalimentación no puede estar vacía")

    revision = _obtener_revision(db, idea_id)
    _validar_revisor_asignado(revision, usuario_actual)
    if revision.estado != EstadoRevision.pendiente_revision:
        raise HTTPException(status_code=400, detail="Esta idea ya no está pendiente de revisión")

    texto = payload.retroalimentacion.strip()

    revision.estado = EstadoRevision.cambios_solicitados
    revision.retroalimentacion = texto
    revision.fecha_resolucion = datetime.now(timezone.utc)

    db.add(
        HistorialRetroalimentacion(
            revision_id=revision.id,
            retroalimentacion=texto,
            creada_por_id=usuario_actual.id,
        )
    )

    orden = siguiente_orden(db, revision.idea_id)
    db.add(
        MensajeEntrevista(
            idea_id=revision.idea_id,
            rol=RolMensaje.asistente,
            contenido=texto,
            orden=orden,
        )
    )

    db.commit()
    db.refresh(revision)
    return revision


@router.post("/{idea_id}/reasignar", response_model=schemas.RevisionOut)
def reasignar(
    idea_id: int,
    payload: schemas.ReasignarRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    """PROPONE una reasignación; ya no la ejecuta.

    Antes este endpoint movía revisor_id de inmediato y la persona destino
    se enteraba al ver la idea aparecer en su lista. Ahora queda en
    pendiente_aceptacion_reasignacion y el destino debe aceptar o rechazar.

    revisor_id NO se toca acá: hasta la aceptación, la idea sigue siendo
    responsabilidad de quien la tiene. Ver RevisionIdea.propuesto_a_id.

    Usa obtener_bloqueado_para_reasignar (FOR UPDATE) en vez de
    _obtener_revision: dos propuestas casi simultáneas sobre la misma idea
    no deben poder pisarse — ver core/reasignacion.py.
    """
    revision = obtener_bloqueado_para_reasignar(db, RevisionIdea, idea_id)
    if not revision:
        raise HTTPException(status_code=404, detail="No existe revisión para esta idea")
    _validar_revisor_asignado(revision, usuario_actual)
    if revision.estado != EstadoRevision.pendiente_revision:
        raise HTTPException(status_code=400, detail="Esta idea ya no está pendiente de revisión")

    nuevo_revisor = _validar_revisor_destino(db, payload.nuevo_revisor_id)
    if nuevo_revisor.id == revision.revisor_id:
        raise HTTPException(status_code=400, detail="Esa persona ya es la revisora de esta idea")

    db.add(
        HistorialIdea(
            idea_id=idea_id,
            tipo_evento=TipoEventoIdea.reasignacion_solicitada,
            actor_id=usuario_actual.id,
            sujeto_id=nuevo_revisor.id,
            detalle=payload.motivo,
        )
    )

    revision.propuesto_a_id = nuevo_revisor.id
    revision.reasignacion_solicitada_por_id = usuario_actual.id
    revision.fecha_solicitud_reasignacion = datetime.now(timezone.utc)
    revision.estado = EstadoRevision.pendiente_aceptacion_reasignacion
    db.commit()
    db.refresh(revision)
    return revision


def _validar_revisor_propuesto(revision: RevisionIdea, usuario_actual: usuarios_models.Usuario) -> None:
    if revision.estado != EstadoRevision.pendiente_aceptacion_reasignacion:
        raise HTTPException(status_code=400, detail="Esta idea no tiene una reasignación pendiente de respuesta")
    # A diferencia del resto de acciones, acá NO hay atajo de admin por
    # defecto: aceptar en nombre de otro sería falsear el consentimiento
    # que todo este flujo existe para registrar.
    if revision.propuesto_a_id != usuario_actual.id:
        raise HTTPException(status_code=403, detail="No sos la persona propuesta para esta revisión")


@router.post("/{idea_id}/aceptar-reasignacion", response_model=schemas.RevisionOut)
def aceptar_reasignacion(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    revision = _obtener_revision(db, idea_id)
    _validar_revisor_propuesto(revision, usuario_actual)

    db.add(
        HistorialIdea(
            idea_id=idea_id,
            tipo_evento=TipoEventoIdea.reasignacion_aceptada,
            actor_id=usuario_actual.id,
            sujeto_id=usuario_actual.id,
        )
    )

    # Recién acá se transfiere la titularidad.
    revision.revisor_id = usuario_actual.id
    revision.propuesto_a_id = None
    revision.reasignacion_solicitada_por_id = None
    revision.fecha_solicitud_reasignacion = None
    revision.rechazos_reasignacion_consecutivos = 0
    revision.estado = EstadoRevision.pendiente_revision
    revision.fecha_asignacion = datetime.now(timezone.utc)
    revision.origen_asignacion = OrigenAsignacion.manual
    db.commit()
    db.refresh(revision)
    return revision


@router.post("/{idea_id}/rechazar-reasignacion", response_model=schemas.RevisionOut)
def rechazar_reasignacion(
    idea_id: int,
    payload: schemas.RechazarReasignacionRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    revision = _obtener_revision(db, idea_id)
    _validar_revisor_propuesto(revision, usuario_actual)

    aplicar_rechazo_reasignacion(
        db,
        revision,
        actor_id=usuario_actual.id,
        tipo_evento=TipoEventoIdea.reasignacion_rechazada,
        detalle=payload.motivo,
    )
    db.commit()
    db.refresh(revision)
    return revision


@router.post("/expirar-reasignaciones", response_model=list[schemas.RevisionOut])
def expirar_reasignaciones(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    """Aplica la política de rechazo a las propuestas que pasaron el
    plazo. Mismo patrón manual que POST /notificaciones/revisar — no hay
    job programado en el sistema todavía."""
    expiradas = expirar_reasignaciones_vencidas(db)
    db.commit()
    for revision in expiradas:
        db.refresh(revision)
    return expiradas


@router.get("/{idea_id}/historial", response_model=list[schemas.HistorialRetroalimentacionOut])
def historial_retroalimentacion(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    revision = _obtener_revision(db, idea_id)

    es_admin = usuario_actual.rol == usuarios_models.RolUsuario.admin
    es_revisor = revision.revisor_id == usuario_actual.id
    es_autor = revision.idea.autor_id == usuario_actual.id
    if not (es_admin or es_revisor or es_autor):
        raise HTTPException(status_code=403, detail="No tienes acceso al historial de esta revisión")

    return (
        db.query(HistorialRetroalimentacion)
        .filter(HistorialRetroalimentacion.revision_id == revision.id)
        .order_by(HistorialRetroalimentacion.creada_en.asc())
        .all()
    )
