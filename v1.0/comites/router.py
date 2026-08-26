import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from comites import schemas
from comites.models import ComiteIdea, EstadoComite, RiceEvaluacion
from comites.rice import calcular_calificacion
from comites.service import departamentos_visibles, idea_departamento_visible
from core.database import get_db
from core.reasignacion import aplicar_rechazo_reasignacion as _aplicar_rechazo_generico
from core.reasignacion import obtener_bloqueado_para_reasignar
from core.rechazo import validar_motivo_rechazo
from ideas.models import HistorialIdea, Idea, TipoEventoIdea
from usuarios import models as usuarios_models
from usuarios import schemas as usuarios_schemas
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/comites", tags=["comites"])
logger = logging.getLogger(__name__)


def _validar_acceso_comite_idea(db: Session, usuario: usuarios_models.Usuario, comite: ComiteIdea) -> None:
    if usuario.rol == usuarios_models.RolUsuario.admin:
        return
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    departamentos = departamentos_visibles(db, usuario)
    if not idea_departamento_visible(comite.idea.autor.departamento_id, departamentos):
        raise HTTPException(
            status_code=403, detail="Esta idea no pertenece a un departamento asignado a tu CAB"
        )


@router.get("/cola", response_model=list[schemas.ComiteIdeaDetalleOut])
def cola_comite(
    estado: EstadoComite = EstadoComite.pendiente,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    # estado por defecto sigue siendo "pendiente" — el parámetro se agregó
    # para que PaginaInicio.tsx pueda pedir estado=aprobada y calcular el
    # conteo de "Aprobadas" del dashboard sin necesitar un endpoint nuevo.
    departamentos = departamentos_visibles(db, usuario_actual)
    if departamentos == []:
        return []
    query = (
        db.query(ComiteIdea)
        .join(Idea, ComiteIdea.idea_id == Idea.id)
        .join(usuarios_models.Usuario, Idea.autor_id == usuarios_models.Usuario.id)
        .filter(ComiteIdea.estado == estado)
    )
    if departamentos is not None:
        # OR ... IS NULL: un autor sin departamento_id asignado debe seguir
        # siendo visible para cualquier miembro de CAB — un filtro IN() solo
        # nunca matchea NULL en SQL y la idea desaparecería en silencio (ver
        # comites/service.py:idea_departamento_visible).
        query = query.filter(
            or_(
                usuarios_models.Usuario.departamento_id.in_(departamentos),
                usuarios_models.Usuario.departamento_id.is_(None),
            )
        )
    resultado = query.order_by(ComiteIdea.creado_en.asc(), ComiteIdea.id.asc()).all()

    if departamentos is not None:
        sin_departamento = [c.idea_id for c in resultado if c.idea.autor.departamento_id is None]
        if sin_departamento:
            logger.warning(
                "cola_comite: %s idea(s) de autores sin departamento_id visibles para "
                "usuario_id=%s por el fallback de departamento nulo: idea_ids=%s",
                len(sin_departamento), usuario_actual.id, sin_departamento,
            )
    return resultado


@router.get("/mis-departamentos", response_model=list[schemas.DepartamentoVisibleOut])
def mis_departamentos(
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    """Para el badge "Viendo: X, Y" del frontend. None (admin / comodín)
    se traduce a la lista completa de departamentos — a un admin o a un
    miembro comodín igual les sirve saber que ven "todos"."""
    ids = departamentos_visibles(db, usuario_actual)
    query = db.query(usuarios_models.Departamento)
    if ids is not None:
        query = query.filter(usuarios_models.Departamento.id.in_(ids))
    return query.order_by(usuarios_models.Departamento.nombre).all()


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
    _validar_acceso_comite_idea(db, usuario_actual, comite)
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
    motivo = validar_motivo_rechazo(payload.motivo_rechazo)

    comite = _obtener_comite(db, idea_id)
    _validar_acceso_comite_idea(db, usuario_actual, comite)
    if comite.estado != EstadoComite.pendiente:
        raise HTTPException(status_code=400, detail="Esta idea ya fue resuelta por el comité")

    comite.estado = EstadoComite.rechazada
    comite.motivo_rechazo = motivo
    comite.aprobada_o_rechazada_por_id = usuario_actual.id
    comite.fecha_resolucion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comite)
    return comite


@router.get("/candidatos-reasignar/{idea_id}", response_model=list[usuarios_schemas.UsuarioBasicoOut])
def candidatos_reasignar(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    """Candidatos para el picker de "Reasignar a" de ColaComite.tsx — replica
    EXACTAMENTE la regla que antes vivía client-side sobre listarUsuarios()
    completo (ver diagnóstico hallazgo #2, tanda 3): solo activo + excluir
    a quien pide. SIN filtro de rol ni de departamento — la validación real
    de acceso al departamento la sigue haciendo _validar_miembro_destino al
    confirmar la reasignación, tal como ya lo hacía el filtro client-side
    original (ver el comentario que tenía ColaComite.tsx antes de esta
    migración). idea_id no cambia el filtro hoy — se recibe por simetría
    con GET /revision/candidatos-reasignar/{idea_id} y por si a futuro se
    vuelve idea-específico.

    Devuelve solo UsuarioBasicoOut (id, nombre, departamento_id) — sin rol
    ni correo."""
    comite = _obtener_comite(db, idea_id)
    return (
        db.query(usuarios_models.Usuario)
        .filter(
            usuarios_models.Usuario.activo == True,  # noqa: E712
            usuarios_models.Usuario.id != usuario_actual.id,
            # El != usuario_actual.id de arriba excluye a QUIEN reasigna; este
            # excluye al AUTOR de la idea, que es otra persona salvo casualidad.
            # Sin él, el picker ofrecía al autor y el 400 de
            # _validar_miembro_destino recién aparecía al confirmar.
            usuarios_models.Usuario.id != comite.idea.autor_id,
        )
        .all()
    )


def _validar_miembro_destino(db: Session, comite: ComiteIdea, usuario_id: int) -> usuarios_models.Usuario:
    destino = db.get(usuarios_models.Usuario, usuario_id)
    if not destino:
        raise HTTPException(status_code=404, detail="El usuario destino no existe")
    # Nadie decide sobre su propia idea. Mismo criterio que
    # revision/router.py:_validar_revisor_destino: la etapa cambia, la regla no.
    if destino.id == comite.idea.autor_id:
        raise HTTPException(
            status_code=400,
            detail=f"'{destino.nombre}' es quien propuso esta idea: no puede decidir sobre la propia",
        )
    if not destino.activo:
        raise HTTPException(status_code=400, detail=f"'{destino.nombre}' está inactivo")
    # Debe ser miembro de CAB con acceso al departamento de ESTA idea
    # (comodín sin filas también califica) — mismo criterio que
    # _validar_acceso_comite_idea, evaluado para la persona destino.
    if destino.rol == usuarios_models.RolUsuario.admin:
        return destino
    departamentos = departamentos_visibles(db, destino)
    if not idea_departamento_visible(comite.idea.autor.departamento_id, departamentos):
        raise HTTPException(
            status_code=400, detail=f"'{destino.nombre}' no tiene acceso al departamento de esta idea"
        )
    return destino


@router.post("/{idea_id}/reasignar", response_model=schemas.ComiteIdeaOut)
def reasignar(
    idea_id: int,
    payload: schemas.ReasignarComiteRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    """PROPONE que otro miembro del CAB atienda esta idea — no ejecuta el
    cambio de inmediato, mismo patrón que revision/router.py:reasignar.

    Usa obtener_bloqueado_para_reasignar (FOR UPDATE) en vez de
    _obtener_comite: dos propuestas casi simultáneas sobre la misma idea no
    deben poder pisarse — ver core/reasignacion.py."""
    comite = obtener_bloqueado_para_reasignar(db, ComiteIdea, idea_id)
    if not comite:
        raise HTTPException(status_code=404, detail="No existe registro de comité para esta idea")
    _validar_acceso_comite_idea(db, usuario_actual, comite)
    if comite.estado != EstadoComite.pendiente:
        raise HTTPException(status_code=400, detail="Esta idea no está pendiente en el comité")

    nuevo = _validar_miembro_destino(db, comite, payload.nuevo_asignado_id)
    if nuevo.id == comite.asignado_a_id:
        raise HTTPException(status_code=400, detail="Esa persona ya está asignada a esta idea")

    db.add(
        HistorialIdea(
            idea_id=idea_id,
            tipo_evento=TipoEventoIdea.reasignacion_solicitada,
            actor_id=usuario_actual.id,
            sujeto_id=nuevo.id,
            detalle=payload.motivo,
        )
    )
    comite.propuesto_a_id = nuevo.id
    comite.reasignacion_solicitada_por_id = usuario_actual.id
    comite.fecha_solicitud_reasignacion = datetime.now(timezone.utc)
    comite.estado = EstadoComite.pendiente_aceptacion_reasignacion
    db.commit()
    db.refresh(comite)
    return comite


def _validar_propuesto(comite: ComiteIdea, usuario_actual: usuarios_models.Usuario) -> None:
    if comite.estado != EstadoComite.pendiente_aceptacion_reasignacion:
        raise HTTPException(status_code=400, detail="Esta idea no tiene una reasignación pendiente de respuesta")
    if comite.propuesto_a_id != usuario_actual.id:
        raise HTTPException(status_code=403, detail="No sos la persona propuesta para esta idea")


@router.post("/{idea_id}/aceptar-reasignacion", response_model=schemas.ComiteIdeaOut)
def aceptar_reasignacion(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    comite = _obtener_comite(db, idea_id)
    _validar_propuesto(comite, usuario_actual)

    db.add(
        HistorialIdea(
            idea_id=idea_id,
            tipo_evento=TipoEventoIdea.reasignacion_aceptada,
            actor_id=usuario_actual.id,
            sujeto_id=usuario_actual.id,
        )
    )
    comite.asignado_a_id = usuario_actual.id
    comite.propuesto_a_id = None
    comite.reasignacion_solicitada_por_id = None
    comite.fecha_solicitud_reasignacion = None
    comite.rechazos_reasignacion_consecutivos = 0
    comite.estado = EstadoComite.pendiente
    db.commit()
    db.refresh(comite)
    return comite


@router.post("/{idea_id}/rechazar-reasignacion", response_model=schemas.ComiteIdeaOut)
def rechazar_reasignacion(
    idea_id: int,
    payload: schemas.RechazarReasignacionComiteRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    comite = _obtener_comite(db, idea_id)
    _validar_propuesto(comite, usuario_actual)

    # ComiteIdea no tiene un estado "sin asignar" bloqueante equivalente a
    # pendiente_asignacion — al segundo rechazo consecutivo simplemente
    # vuelve a pendiente con asignado_a_id=None (ver core/reasignacion.py).
    _aplicar_rechazo_generico(
        db,
        comite,
        campo_responsable="asignado_a_id",
        estado_sin_asignar=None,
        estado_normal=EstadoComite.pendiente,
        idea_id=idea_id,
        actor_id=usuario_actual.id,
        tipo_evento=TipoEventoIdea.reasignacion_rechazada,
        detalle=payload.motivo,
    )
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
    _validar_acceso_comite_idea(db, usuario_actual, comite)

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
    _validar_acceso_comite_idea(db, usuario_actual, comite)

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
