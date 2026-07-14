from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.models import ComiteIdea, EstadoComite
from core.database import get_db
from notificaciones import schemas
from notificaciones.models import ConfiguracionEscalamiento, EtapaEscalamiento, NotificacionEscalamiento
from revision.models import EstadoRevision, RevisionIdea
from usuarios import models as usuarios_models
from usuarios.dependencies import requerir_admin

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def _obtener_configuracion(db: Session, etapa: EtapaEscalamiento) -> ConfiguracionEscalamiento:
    config = db.query(ConfiguracionEscalamiento).filter_by(etapa=etapa).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"No existe configuración para la etapa {etapa.value}")
    return config


@router.get("/config/{etapa}", response_model=schemas.ConfiguracionEscalamientoOut)
def obtener_config(
    etapa: EtapaEscalamiento,
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    return _obtener_configuracion(db, etapa)


@router.put("/config/{etapa}", response_model=schemas.ConfiguracionEscalamientoOut)
def actualizar_config(
    etapa: EtapaEscalamiento,
    payload: schemas.ConfiguracionEscalamientoUpdate,
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    config = _obtener_configuracion(db, etapa)
    config.plazo_dias = payload.plazo_dias
    config.responsable_id = payload.responsable_id
    db.commit()
    db.refresh(config)
    return config


# Por cada etapa: el modelo, el estado (o estados) que cuentan como "pendiente",
# y de qué columna de fecha se mide la antigüedad.
_ETAPAS_PENDIENTES = {
    EtapaEscalamiento.revision: (
        RevisionIdea,
        [EstadoRevision.pendiente_asignacion, EstadoRevision.pendiente_revision],
        RevisionIdea.creado_en,
    ),
    EtapaEscalamiento.clasificacion: (
        ClasificacionIdea,
        [EstadoClasificacion.pendiente_clasificacion],
        ClasificacionIdea.creado_en,
    ),
    EtapaEscalamiento.comites: (
        ComiteIdea,
        [EstadoComite.pendiente],
        ComiteIdea.creado_en,
    ),
}


@router.post("/revisar", response_model=schemas.RevisarResultadoOut)
def revisar(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    ahora = datetime.now(timezone.utc)
    generadas: list[NotificacionEscalamiento] = []

    configs = (
        db.query(ConfiguracionEscalamiento)
        .filter(ConfiguracionEscalamiento.plazo_dias.isnot(None))
        .all()
    )

    for config in configs:
        modelo, estados_pendientes, columna_fecha = _ETAPAS_PENDIENTES[config.etapa]
        pendientes = db.query(modelo).filter(modelo.estado.in_(estados_pendientes)).all()

        for registro in pendientes:
            fecha_base = getattr(registro, columna_fecha.key)
            if fecha_base is None:
                continue
            dias_transcurridos = (ahora - fecha_base).days
            if dias_transcurridos < config.plazo_dias:
                continue

            ya_notificada = (
                db.query(NotificacionEscalamiento.id)
                .filter(
                    NotificacionEscalamiento.etapa == config.etapa,
                    NotificacionEscalamiento.idea_id == registro.idea_id,
                )
                .first()
                is not None
            )
            if ya_notificada:
                continue

            notificacion = NotificacionEscalamiento(
                etapa=config.etapa,
                idea_id=registro.idea_id,
                responsable_id=config.responsable_id,
                dias_transcurridos=dias_transcurridos,
            )
            db.add(notificacion)
            generadas.append(notificacion)

    db.commit()
    for notificacion in generadas:
        db.refresh(notificacion)

    return schemas.RevisarResultadoOut(
        notificaciones_generadas=len(generadas),
        notificaciones=generadas,
    )


@router.get("", response_model=list[schemas.NotificacionEscalamientoOut])
def listar_notificaciones(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    return (
        db.query(NotificacionEscalamiento)
        .order_by(NotificacionEscalamiento.generada_en.desc())
        .all()
    )
