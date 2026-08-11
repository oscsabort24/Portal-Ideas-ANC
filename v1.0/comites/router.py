from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from comites import schemas
from comites.models import ComiteIdea, EstadoComite, RiceEvaluacion
from comites.rice import calcular_calificacion
from core.database import get_db
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
    estado: EstadoComite = EstadoComite.pendiente,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    # estado por defecto sigue siendo "pendiente" (comportamiento de siempre,
    # la cola real de trabajo) — el parámetro se agregó para que
    # PaginaInicio.tsx pueda pedir estado=aprobada y calcular el conteo de
    # "Aprobadas" del dashboard sin necesitar un endpoint nuevo.
    _validar_acceso_comite(db, usuario_actual, tipo_cab)
    return (
        db.query(ComiteIdea)
        .filter(ComiteIdea.tipo_cab == tipo_cab, ComiteIdea.estado == estado)
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
    # La generación de documentos ya NO es automática — ver
    # POST /documentos/{idea_id}/generar, disparado manualmente por quien
    # aprueba (o cualquiera con acceso, después).
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


@router.get("/{idea_id}/rice", response_model=schemas.RiceEvaluacionOut)
def obtener_rice(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    comite = _obtener_comite(db, idea_id)
    _validar_acceso_comite(db, usuario_actual, comite.tipo_cab)

    rice = db.query(RiceEvaluacion).filter_by(comite_idea_id=comite.id).first()
    if not rice:
        raise HTTPException(status_code=404, detail="Esta idea todavía no tiene una evaluación RICE")
    return rice


@router.put("/{idea_id}/rice", response_model=schemas.RiceEvaluacionOut)
def guardar_rice(
    idea_id: int,
    payload: schemas.RiceEvaluacionRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    comite = _obtener_comite(db, idea_id)
    _validar_acceso_comite(db, usuario_actual, comite.tipo_cab)

    # calificacion/prioridad SIEMPRE se recalculan acá, nunca se acepta un
    # valor del cliente para esos dos campos (ver comites/rice.py).
    calificacion, prioridad = calcular_calificacion(
        alcance_departamentos=payload.alcance_departamentos,
        impacto=payload.impacto,
        confianza=payload.confianza,
        esfuerzo=payload.esfuerzo,
        paises=payload.paises,
        presupuesto_rango=payload.presupuesto_rango,
        impacta_plan_estrategico=payload.impacta_plan_estrategico,
    )

    rice = db.query(RiceEvaluacion).filter_by(comite_idea_id=comite.id).first()
    if not rice:
        rice = RiceEvaluacion(comite_idea_id=comite.id)
        db.add(rice)

    rice.area = payload.area.strip()
    rice.lider_funcional = payload.lider_funcional.strip()
    rice.paises = payload.paises
    rice.presupuesto_rango = payload.presupuesto_rango
    rice.impacta_plan_estrategico = payload.impacta_plan_estrategico
    rice.alcance_departamentos = payload.alcance_departamentos
    rice.impacto = payload.impacto
    rice.confianza = payload.confianza
    rice.esfuerzo = payload.esfuerzo
    rice.calificacion = calificacion
    rice.prioridad = prioridad
    rice.completado_por_id = usuario_actual.id

    db.commit()
    db.refresh(rice)
    return rice
