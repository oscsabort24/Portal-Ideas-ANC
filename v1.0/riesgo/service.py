"""Creación del análisis de riesgo automático, llamado desde
ideas/router.py al completar la entrevista (mismo punto donde se crea
RevisionIdea). Es informativo y NUNCA bloqueante — ver docstring de
AnalisisRiesgoIdea.
"""

import logging

from sqlalchemy.orm import Session

from core.claude_client import analizar_riesgo_idea
from ideas.models import Idea
from riesgo.models import AnalisisRiesgoIdea, CategoriaRiesgo

logger = logging.getLogger(__name__)


def categoria_desde_nivel(nivel: int) -> CategoriaRiesgo:
    """Tabla exacta de la política de ANC: 1-5 Bajo, 6-10 Moderado,
    11-15 Medio-Alto, 16-20 Alto, 21-25 Crítico."""
    if nivel <= 5:
        return CategoriaRiesgo.bajo
    if nivel <= 10:
        return CategoriaRiesgo.moderado
    if nivel <= 15:
        return CategoriaRiesgo.medio_alto
    if nivel <= 20:
        return CategoriaRiesgo.alto
    return CategoriaRiesgo.critico


def crear_analisis_riesgo_para_idea(db: Session, idea: Idea, historial: list[dict]) -> AnalisisRiesgoIdea | None:
    """Devuelve None (sin crear nada) si la IA falla por cualquier motivo
    — el caller (ideas/router.py) no debe tratar eso como un error, solo
    seguir sin análisis de riesgo."""
    try:
        resultado = analizar_riesgo_idea(historial)
    except Exception:
        logger.exception("analisis de riesgo automatico fallo para idea %s", idea.id)
        return None

    if resultado is None:
        return None

    nivel_riesgo = resultado["probabilidad"] * resultado["impacto"]
    analisis = AnalisisRiesgoIdea(
        idea_id=idea.id,
        probabilidad=resultado["probabilidad"],
        impacto=resultado["impacto"],
        nivel_riesgo=nivel_riesgo,
        categoria=categoria_desde_nivel(nivel_riesgo),
        justificacion=resultado["justificacion"],
    )
    db.add(analisis)
    return analisis
