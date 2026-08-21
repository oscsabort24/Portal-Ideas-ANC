"""Creación del registro de cola de comité (llamada desde
clasificacion/router.py al clasificar una idea) y resolución de qué
departamentos puede ver/atender un miembro de CAB — compartida entre
comites/router.py y documentos/router.py (ver
diseno-pendiente/cab-departamento-reasignacion.md.preview)."""

import logging

from sqlalchemy.orm import Session

from comites.models import ComiteIdea, EstadoComite
from ideas.models import Idea
from usuarios.models import MiembroCAB, MiembroCABDepartamento, RolUsuario, TipoCAB, Usuario

logger = logging.getLogger(__name__)


def crear_comite_idea_para_idea(db: Session, idea: Idea, tipo_cab: TipoCAB) -> ComiteIdea:
    # Mismo motivo que clasificacion/service.py:crear_clasificacion_para_idea — evita
    # IntegrityError (idea_id es unique) si esta función llega a ejecutarse dos veces
    # para la misma idea (ej. dos aprobaciones en carrera de la misma revisión).
    existente = db.query(ComiteIdea).filter_by(idea_id=idea.id).first()
    if existente is not None:
        existente.estado = EstadoComite.pendiente
        existente.tipo_cab = tipo_cab
        existente.motivo_rechazo = None
        existente.aprobada_o_rechazada_por_id = None
        existente.fecha_resolucion = None
        return existente

    comite = ComiteIdea(idea_id=idea.id, tipo_cab=tipo_cab, estado=EstadoComite.pendiente)
    db.add(comite)
    return comite


def departamentos_visibles(db: Session, usuario: Usuario) -> list[int] | None:
    """None = ve todos los departamentos (admin, o miembro de CAB sin
    filas en miembros_cab_departamentos — ausencia de filas = "todos").
    Lista vacía = no es miembro de ningún CAB, no ve nada."""
    if usuario.rol == RolUsuario.admin:
        return None
    membresias = db.query(MiembroCAB).filter_by(usuario_id=usuario.id).all()
    if not membresias:
        return []
    ids = {
        d.departamento_id
        for m in membresias
        for d in db.query(MiembroCABDepartamento).filter_by(miembro_cab_id=m.id).all()
    }
    return list(ids) if ids else None


def idea_departamento_visible(departamento_idea_id: int | None, departamentos: list[int] | None) -> bool:
    """¿Un miembro de CAB con este `departamentos` (resultado de
    departamentos_visibles) puede ver/atender una idea cuyo autor tiene
    `departamento_idea_id`?

    `departamento_idea_id is None` (autor sin departamento asignado —
    Usuario.departamento_id es nullable) SIEMPRE se considera visible, para
    cualquier miembro de CAB, no solo admin: un filtro `IN (departamentos)`
    nunca matchea NULL en SQL, así que sin este caso especial la idea
    desaparecía silenciosamente de toda cola salvo la de admin — mejor que
    se vea de más (cualquier CAB puede atenderla) a que se pierda sin que
    nadie lo note. Se loguea como warning porque es una situación de datos
    anómala (un autor sin departamento) que debería ser rara y detectable
    en producción, no un flujo normal silencioso."""
    if departamento_idea_id is None:
        if departamentos is not None:
            logger.warning(
                "Idea de un autor sin departamento_id asignado — visible para todos los "
                "miembros de CAB en vez de filtrarse por departamento (departamentos_visibles=%s)",
                departamentos,
            )
        return True
    return departamentos is None or departamento_idea_id in departamentos
