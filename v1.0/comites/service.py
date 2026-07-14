"""Creación del registro de cola de comité, llamada desde clasificacion/router.py al clasificar una idea."""

from sqlalchemy.orm import Session

from comites.models import ComiteIdea, EstadoComite
from ideas.models import Idea
from usuarios.models import TipoCAB


def crear_comite_idea_para_idea(db: Session, idea: Idea, tipo_cab: TipoCAB) -> ComiteIdea:
    comite = ComiteIdea(idea_id=idea.id, tipo_cab=tipo_cab, estado=EstadoComite.pendiente)
    db.add(comite)
    return comite
