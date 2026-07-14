import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación ClasificacionIdea.idea
from usuarios.models import TipoCAB, Usuario  # noqa: F401 — necesario para resolver la relación .clasificado_por


class EstadoClasificacion(str, enum.Enum):
    pendiente_clasificacion = "pendiente_clasificacion"
    clasificada = "clasificada"


class ClasificacionIdea(Base):
    """Clasificación de una idea aprobada (Innovación vs Transformación Digital).

    Se crea automáticamente cuando la revisión de una idea pasa a estado
    "aprobada" (ver clasificacion/service.py:crear_clasificacion_para_idea,
    llamado desde revision/router.py:aprobar). Nace siempre en
    pendiente_clasificacion con clasificacion=None — NO existe ninguna regla
    automática (palabras clave, heurística, etc.) que infiera la clasificación;
    solo un admin puede clasificarla manualmente mientras no haya un criterio
    de negocio real definido (pendiente de que Armando lo defina).

    Reutiliza usuarios.models.TipoCAB (innovacion / transformacion_digital)
    en vez de un enum propio — es el mismo concepto de negocio que ya usa
    MiembroCAB.
    """

    __tablename__ = "clasificacion_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)
    estado: Mapped[EstadoClasificacion] = mapped_column(
        Enum(EstadoClasificacion, name="estado_clasificacion"), nullable=False
    )
    clasificacion: Mapped[TipoCAB | None] = mapped_column(
        Enum(TipoCAB, name="tipo_cab_clasificacion"), nullable=True
    )

    clasificado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    clasificado_por: Mapped["Usuario | None"] = relationship()
    fecha_clasificacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
