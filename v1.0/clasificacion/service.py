"""Creación del registro de clasificación, llamada desde revision/router.py al aprobar una idea.

*** SIN CLASIFICACIÓN AUTOMÁTICA ***
No existe ninguna regla (palabras clave, heurística, etc.) que infiera
Innovación vs Transformación Digital — sería inventar el criterio de negocio
real que le corresponde definir a Armando. Toda idea aprobada nace
"pendiente_clasificacion" con clasificacion=None, y solo un admin la
clasifica manualmente desde la UI.
"""

from sqlalchemy.orm import Session

from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from ideas.models import Idea


def crear_clasificacion_para_idea(db: Session, idea: Idea) -> ClasificacionIdea:
    clasificacion = ClasificacionIdea(
        idea_id=idea.id,
        estado=EstadoClasificacion.pendiente_clasificacion,
        clasificacion=None,
    )
    db.add(clasificacion)
    return clasificacion
