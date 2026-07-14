import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación ComiteIdea.idea
from usuarios.models import TipoCAB, Usuario  # noqa: F401 — necesario para resolver la relación .aprobada_o_rechazada_por


class EstadoComite(str, enum.Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"


class ComiteIdea(Base):
    """Paso de una idea clasificada por la cola del CAB correspondiente.

    Se crea automáticamente cuando un admin clasifica la idea (ver
    comites/service.py:crear_comite_idea_para_idea, llamado desde
    clasificacion/router.py:clasificar). `tipo_cab` se copia de la
    clasificación al momento de crearse, para no depender de un join
    extra después.

    El orden de llegada a la cola es simplemente `creado_en` (+ `id`
    como desempate) — no hay un contador explícito porque cada fila se
    crea una sola vez desde un único punto de integración, sin riesgo
    real de carrera.

    El estado final "aprobada_por_cab" vive únicamente en `estado` de
    este modelo — no se refleja en Idea.estado, que describe solo la
    etapa de captura (borrador/enviada).
    """

    __tablename__ = "comite_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)
    tipo_cab: Mapped[TipoCAB] = mapped_column(Enum(TipoCAB, name="tipo_cab_comite"), nullable=False)
    estado: Mapped[EstadoComite] = mapped_column(Enum(EstadoComite, name="estado_comite"), nullable=False)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    aprobada_o_rechazada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    aprobada_o_rechazada_por: Mapped["Usuario | None"] = relationship()
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
