from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from comites import schemas
from comites.models import ComiteIdea, EstadoComite
from core.database import get_db
from documentos.service import generar_documentos_para_idea
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/comites", tags=["comites"])


def _validar_acceso_comite(
    db: Session, usuario: usuarios_models.Usuario, tipo_cab: usuarios_models.TipoCAB
) -> None:
    if usuario.rol == usuarios_models.RolUsuario.admin:
        return
    es_miembro = (
        db.query(usuarios_models.MiembroCAB)
        .filter(
            usuarios_models.MiembroCAB.usuario_id == usuario.id,
            usuarios_models.MiembroCAB.tipo_cab == tipo_cab,
        )
        .first()
        is not None
    )
    if not es_miembro or not usuario.activo:
        raise HTTPException(status_code=403, detail=f"No eres miembro del CAB de {tipo_cab.value}")


@router.get("/{tipo_cab}/cola", response_model=list[schemas.ComiteIdeaDetalleOut])
def cola_comite(
    tipo_cab: usuarios_models.TipoCAB,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    _validar_acceso_comite(db, usuario_actual, tipo_cab)
    return (
        db.query(ComiteIdea)
        .filter(ComiteIdea.tipo_cab == tipo_cab, ComiteIdea.estado == EstadoComite.pendiente)
        .order_by(ComiteIdea.creado_en.asc(), ComiteIdea.id.asc())
        .all()
    )


def _obtener_comite(db: Session, idea_id: int) -> ComiteIdea:
    comite = db.query(ComiteIdea).filter_by(idea_id=idea_id).first()
    if not comite:
        raise HTTPException(status_code=404, detail="No existe registro de comité para esta idea")
    return comite


@router.post("/{idea_id}/aprobar", response_model=schemas.ComiteIdeaOut)
def aprobar(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    comite = _obtener_comite(db, idea_id)
    _validar_acceso_comite(db, usuario_actual, comite.tipo_cab)
    if comite.estado != EstadoComite.pendiente:
        raise HTTPException(status_code=400, detail="Esta idea ya fue resuelta por el comité")

    comite.estado = EstadoComite.aprobada
    comite.aprobada_o_rechazada_por_id = usuario_actual.id
    comite.fecha_resolucion = datetime.now(timezone.utc)
    generar_documentos_para_idea(db, comite.idea)
    db.commit()
    db.refresh(comite)
    return comite


@router.post("/{idea_id}/rechazar", response_model=schemas.ComiteIdeaOut)
def rechazar(
    idea_id: int,
    payload: schemas.RechazarRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    if not payload.motivo_rechazo.strip():
        raise HTTPException(status_code=400, detail="El motivo de rechazo no puede estar vacío")

    comite = _obtener_comite(db, idea_id)
    _validar_acceso_comite(db, usuario_actual, comite.tipo_cab)
    if comite.estado != EstadoComite.pendiente:
        raise HTTPException(status_code=400, detail="Esta idea ya fue resuelta por el comité")

    comite.estado = EstadoComite.rechazada
    comite.motivo_rechazo = payload.motivo_rechazo.strip()
    comite.aprobada_o_rechazada_por_id = usuario_actual.id
    comite.fecha_resolucion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comite)
    return comite
