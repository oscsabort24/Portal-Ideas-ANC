"""Lógica de asignación de revisión, llamada desde ideas/router.py cuando una idea se envía.

*** REGLA DE ASIGNACIÓN TEMPORAL ***
Asigna al encargado_area del mismo departamento que el autor. Esto es un
placeholder mientras Armando define el criterio real de asignación por
contenido de la idea (ver README de este módulo). Si no hay ningún
encargado_area activo en ese departamento — caso esperado hoy, mientras se
termina de poblar personas reales — la idea queda "pendiente_asignacion"
para que un admin la asigne manualmente. Nunca falla ni se pierde.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ideas.models import Idea
from revision.models import EstadoRevision, RevisionIdea
from usuarios.models import RolUsuario, Usuario


def crear_revision_para_idea(db: Session, idea: Idea) -> RevisionIdea:
    revisor = None
    if idea.autor.departamento_id is not None:
        revisor = (
            db.query(Usuario)
            .filter(
                Usuario.departamento_id == idea.autor.departamento_id,
                Usuario.rol == RolUsuario.encargado_area,
                Usuario.activo == True,  # noqa: E712
            )
            .first()
        )

    ahora = datetime.now(timezone.utc)
    revision = RevisionIdea(
        idea_id=idea.id,
        revisor_id=revisor.id if revisor else None,
        estado=EstadoRevision.pendiente_revision if revisor else EstadoRevision.pendiente_asignacion,
        fecha_asignacion=ahora if revisor else None,
    )
    db.add(revision)
    return revision
