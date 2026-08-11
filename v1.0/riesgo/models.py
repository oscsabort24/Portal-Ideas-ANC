import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación AnalisisRiesgoIdea.idea


class CategoriaRiesgo(str, enum.Enum):
    bajo = "bajo"
    moderado = "moderado"
    medio_alto = "medio_alto"
    alto = "alto"
    critico = "critico"


class AnalisisRiesgoIdea(Base):
    """Análisis de riesgo automático por IA, calculado al completar la
    entrevista (mismo punto donde se crea RevisionIdea — ver
    ideas/router.py:enviar_mensaje). Es INFORMATIVO, no bloqueante: si la
    llamada a la IA falla, la idea simplemente no tiene análisis de
    riesgo — no existe ningún fallback manual ni ninguna decisión de
    negocio que dependa de que este registro exista.

    `nivel_riesgo` y `categoria` SIEMPRE se calculan en código a partir
    de `probabilidad`/`impacto` (nunca se confía en que la IA haga la
    multiplicación ni clasifique la categoría) — ver
    riesgo/service.py:categoria_desde_nivel.
    """

    __tablename__ = "analisis_riesgo_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)

    probabilidad: Mapped[int] = mapped_column(Integer, nullable=False)
    impacto: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel_riesgo: Mapped[int] = mapped_column(Integer, nullable=False)
    categoria: Mapped[CategoriaRiesgo] = mapped_column(
        Enum(CategoriaRiesgo, name="categoria_riesgo"), nullable=False
    )
    justificacion: Mapped[str] = mapped_column(Unicode(), nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
