"""Creación del registro de clasificación, llamada desde revision/router.py al aprobar una idea.

Intenta clasificar automáticamente con IA (Innovación vs Transformación
Digital) cuando existe un DocumentoCriterio activo de tipo "clasificacion"
(subido por Armando vía criterios/). Si no existe ese documento todavía, o
si la llamada a la IA falla por cualquier motivo (API caída, .docx
corrupto, respuesta no parseable), cae al comportamiento de siempre: la
idea nace "pendiente_clasificacion" con clasificacion=None, para que un
admin la clasifique manualmente — este fallback NUNCA debe romper la
transacción de revision/router.py:aprobar, que siempre debe tener éxito.

clasificado_por_id=None distingue una clasificación hecha por la IA de una
hecha por una persona (ver clasificacion/router.py:clasificar, que siempre
llena clasificado_por_id con el admin real que corrige o clasifica a mano).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.service import crear_comite_idea_para_idea
from core.claude_client import clasificar_idea
from criterios.models import CriterioIA, TipoCriterio
from ideas.models import Idea
from ideas.service import historial_para_ia

logger = logging.getLogger(__name__)


def _clasificar_con_ia(db: Session, idea: Idea) -> dict | None:
    criterio = (
        db.query(CriterioIA)
        .filter_by(tipo=TipoCriterio.clasificacion, departamento_id=None, activo=True)
        .first()
    )
    if not criterio:
        return None

    try:
        historial = historial_para_ia(db, idea.id)
        return clasificar_idea(historial, criterio.contenido)
    except Exception:
        # Cualquier fallo (docx corrupto, ruta inválida, etc. — no solo
        # errores de la API, que clasificar_idea ya maneja internamente)
        # degrada a pendiente_clasificacion en vez de romper la aprobación
        # de la revisión.
        logger.exception("clasificacion automatica fallo para idea %s", idea.id)
        return None


def crear_clasificacion_para_idea(db: Session, idea: Idea) -> ClasificacionIdea:
    # Normalmente esta función solo corre una vez por idea (revision/router.py:aprobar
    # exige revision.estado==pendiente_revision, que deja de ser alcanzable en cuanto
    # se aprueba una vez). Pero dos aprobaciones casi simultáneas de la misma revisión
    # (doble-click, dos requests en carrera) pueden colar ambas el guard antes de que
    # la primera haga commit — sin este chequeo, la segunda truena con IntegrityError
    # (idea_id es unique). Reutilizar en vez de crear también deja el código correcto
    # si en el futuro se agrega una forma de reabrir una revisión ya aprobada.
    existente = db.query(ClasificacionIdea).filter_by(idea_id=idea.id).first()
    resultado_ia = _clasificar_con_ia(db, idea)

    if existente is not None:
        if resultado_ia is not None:
            existente.estado = EstadoClasificacion.clasificada
            existente.clasificacion = resultado_ia["clasificacion"]
            existente.clasificado_por_id = None
            existente.fecha_clasificacion = datetime.now(timezone.utc)
            db.flush()
            crear_comite_idea_para_idea(db, idea, resultado_ia["clasificacion"])
        else:
            existente.estado = EstadoClasificacion.pendiente_clasificacion
            existente.clasificacion = None
            existente.clasificado_por_id = None
            existente.fecha_clasificacion = None
        return existente

    if resultado_ia is not None:
        clasificacion = ClasificacionIdea(
            idea_id=idea.id,
            estado=EstadoClasificacion.clasificada,
            clasificacion=resultado_ia["clasificacion"],
            clasificado_por_id=None,
            fecha_clasificacion=datetime.now(timezone.utc),
        )
        db.add(clasificacion)
        db.flush()
        crear_comite_idea_para_idea(db, idea, resultado_ia["clasificacion"])
    else:
        clasificacion = ClasificacionIdea(
            idea_id=idea.id,
            estado=EstadoClasificacion.pendiente_clasificacion,
            clasificacion=None,
        )
        db.add(clasificacion)

    return clasificacion
