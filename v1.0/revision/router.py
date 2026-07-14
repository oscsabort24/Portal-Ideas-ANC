from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from clasificacion.service import crear_clasificacion_para_idea
from core.database import get_db
from ideas.models import MensajeEntrevista, RolMensaje
from ideas.service import siguiente_orden
from revision import schemas
from revision.models import EstadoRevision, HistorialRetroalimentacion, RevisionIdea
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual, requerir_admin

router = APIRouter(prefix="/revision", tags=["revision"])


def _validar_revisor_destino(db: Session, revisor_id: int) -> usuarios_models.Usuario:
    revisor = db.get(usuarios_models.Usuario, revisor_id)
    if not revisor:
        raise HTTPException(status_code=404, detail="El usuario destino no existe")
    if revisor.rol != usuarios_models.RolUsuario.encargado_area:
        raise HTTPException(
            status_code=400,
            detail=f"'{revisor.nombre}' no tiene rol encargado_area, no puede ser revisor",
        )
    if not revisor.activo:
        raise HTTPException(status_code=400, detail=f"'{revisor.nombre}' no puede ser revisor: está inactivo")
    return revisor


@router.get("/mias", response_model=list[schemas.RevisionDetalleOut])
def mis_revisiones(
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    return (
        db.query(RevisionIdea)
        .filter(
            RevisionIdea.revisor_id == usuario_actual.id,
            RevisionIdea.estado == EstadoRevision.pendiente_revision,
        )
        .all()
    )


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
    db.commit()
    db.refresh(revision)
    return revision


def _validar_revisor_asignado(revision: RevisionIdea, usuario_actual: usuarios_models.Usuario) -> None:
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
    revision = _obtener_revision(db, idea_id)
    _validar_revisor_asignado(revision, usuario_actual)
    if revision.estado != EstadoRevision.pendiente_revision:
        raise HTTPException(status_code=400, detail="Esta idea ya no está pendiente de revisión")

    nuevo_revisor = _validar_revisor_destino(db, payload.nuevo_revisor_id)

    revision.revisor_id = nuevo_revisor.id
    revision.fecha_asignacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(revision)
    return revision


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
