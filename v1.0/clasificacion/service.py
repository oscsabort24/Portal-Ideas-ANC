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

from docx import Document
from sqlalchemy.orm import Session

from clasificacion.models import ClasificacionIdea, EstadoClasificacion
from comites.service import crear_comite_idea_para_idea
from core.claude_client import clasificar_idea
from criterios.models import DocumentoCriterio, TipoCriterio
from ideas.models import Idea, MensajeEntrevista

logger = logging.getLogger(__name__)


def _extraer_texto_docx(ruta_archivo: str) -> str:
    documento = Document(ruta_archivo)
    return "\n".join(p.text for p in documento.paragraphs if p.text.strip())


def _historial_para_ia(db: Session, idea_id: int) -> list[dict]:
    mensajes = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    return [{"role": m.rol.value, "content": m.contenido} for m in mensajes]


def _clasificar_con_ia(db: Session, idea: Idea) -> dict | None:
    documento = (
        db.query(DocumentoCriterio)
        .filter_by(tipo=TipoCriterio.clasificacion, activo=True)
        .first()
    )
    if not documento:
        return None

    try:
        criterio_texto = _extraer_texto_docx(documento.ruta_archivo)
        historial = _historial_para_ia(db, idea.id)
        return clasificar_idea(historial, criterio_texto)
    except Exception:
        # Cualquier fallo (docx corrupto, ruta inválida, etc. — no solo
        # errores de la API, que clasificar_idea ya maneja internamente)
        # degrada a pendiente_clasificacion en vez de romper la aprobación
        # de la revisión.
        logger.exception("clasificacion automatica fallo para idea %s", idea.id)
        return None


def crear_clasificacion_para_idea(db: Session, idea: Idea) -> ClasificacionIdea:
    resultado_ia = _clasificar_con_ia(db, idea)

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
