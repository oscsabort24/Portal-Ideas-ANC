"""Creación del registro de cola de comité, llamada desde clasificacion/router.py al clasificar una idea."""

from sqlalchemy.orm import Session

from comites.models import ComiteIdea, EstadoComite
from ideas.models import Idea
from usuarios.models import TipoCAB


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
