from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from clasificacion import schemas
from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.models import ComiteIdea, EstadoComite
from comites.service import crear_comite_idea_para_idea
from core.database import get_db
from usuarios import models as usuarios_models
from usuarios.dependencies import requerir_admin

router = APIRouter(prefix="/clasificacion", tags=["clasificacion"])

# Ambos endpoints usan requerir_admin (no un patrón de "admin + rol funcional
# específico" como en comites/revision/ideas) — decisión intencional
# confirmada: clasificar una idea (Innovación vs Transformación Digital) es
# una corrección de negocio reservada a admin, no delegable a encargado_area
# o gerente. No es una asimetría accidental respecto a los demás módulos.


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

    # Este endpoint ya no solo cubre la primera clasificación (manual, si no
    # hubo IA, o si Armando aún no subió el criterio): también es el
    # mecanismo de corrección humana sobre una clasificación ya hecha por la
    # IA o por otro admin. Lo único que de verdad bloquea reclasificar es
    # que el CAB ya haya resuelto la idea — en ese punto ya no tiene sentido
    # cambiarle el tipo de CAB.
    comite = db.query(ComiteIdea).filter_by(idea_id=idea_id).first()
    if comite and comite.estado != EstadoComite.pendiente:
        raise HTTPException(
            status_code=400,
            detail="No se puede reclasificar: el comité ya resolvió esta idea",
        )

    clasificacion.clasificacion = payload.clasificacion
    clasificacion.estado = EstadoClasificacion.clasificada
    clasificacion.clasificado_por_id = admin.id
    clasificacion.fecha_clasificacion = datetime.now(timezone.utc)

    if comite:
        comite.tipo_cab = payload.clasificacion
    else:
        crear_comite_idea_para_idea(db, clasificacion.idea, payload.clasificacion)

    db.commit()
    db.refresh(clasificacion)
    return clasificacion
