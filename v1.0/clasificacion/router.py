from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from clasificacion import schemas
from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.service import crear_comite_idea_para_idea
from core.database import get_db
from usuarios import models as usuarios_models
from usuarios.dependencies import requerir_admin

router = APIRouter(prefix="/clasificacion", tags=["clasificacion"])


@router.get("/pendientes", response_model=list[schemas.ClasificacionDetalleOut])
def listar_pendientes(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    return (
        db.query(ClasificacionIdea)
        .filter(ClasificacionIdea.estado == EstadoClasificacion.pendiente_clasificacion)
        .all()
    )


@router.post("/{idea_id}/clasificar", response_model=schemas.ClasificacionOut)
def clasificar(
    idea_id: int,
    payload: schemas.ClasificarRequest,
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    clasificacion = db.query(ClasificacionIdea).filter_by(idea_id=idea_id).first()
    if not clasificacion:
        raise HTTPException(status_code=404, detail="No existe clasificación para esta idea")
    if clasificacion.estado != EstadoClasificacion.pendiente_clasificacion:
        raise HTTPException(status_code=400, detail="Esta idea ya fue clasificada")

    clasificacion.clasificacion = payload.clasificacion
    clasificacion.estado = EstadoClasificacion.clasificada
    clasificacion.clasificado_por_id = admin.id
    clasificacion.fecha_clasificacion = datetime.now(timezone.utc)
    crear_comite_idea_para_idea(db, clasificacion.idea, payload.clasificacion)
    db.commit()
    db.refresh(clasificacion)
    return clasificacion
