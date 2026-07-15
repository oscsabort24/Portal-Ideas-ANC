import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación RevisionIdea.idea
from usuarios.models import Usuario  # noqa: F401 — necesario para resolver la relación RevisionIdea.revisor


class EstadoRevision(str, enum.Enum):
    pendiente_asignacion = "pendiente_asignacion"
    pendiente_revision = "pendiente_revision"
    aprobada = "aprobada"
    cambios_solicitados = "cambios_solicitados"


class RevisionIdea(Base):
    """Revisión de una idea enviada, por un encargado_area.

    Se crea automáticamente cuando la idea pasa a estado "enviada"
    (ver revision/service.py:crear_revision_para_idea, llamado desde
    ideas/router.py). Una idea tiene una sola revisión activa (idea_id
    es único).
    """

    __tablename__ = "revision_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)
    revisor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    estado: Mapped[EstadoRevision] = mapped_column(
        Enum(EstadoRevision, name="estado_revision"), nullable=False
    )
    retroalimentacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_asignacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
    revisor: Mapped["Usuario | None"] = relationship()


class HistorialRetroalimentacion(Base):
    """Bitácora append-only de cada ronda de retroalimentación de una revisión.

    Se crea una fila nueva en cada POST /revision/{idea_id}/pedir-cambios
    (ver revision/router.py:pedir_cambios) — nunca se edita ni se borra.
    RevisionIdea.retroalimentacion sigue reflejando solo la más reciente
    (para no depender de un join en las vistas rápidas); este modelo es
    el historial completo para auditoría.
    """

    __tablename__ = "historial_retroalimentacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("revision_ideas.id"), nullable=False)
    retroalimentacion: Mapped[str] = mapped_column(Text, nullable=False)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    revision: Mapped["RevisionIdea"] = relationship()
    creada_por: Mapped["Usuario"] = relationship()


class HistorialReasignacion(Base):
    """Bitácora append-only de cada reasignación de revisor.

    Se crea una fila en cada POST /revision/{idea_id}/reasignar (ver
    revision/router.py:reasignar). POST /revision/{idea_id}/asignar NO
    registra aquí: ese endpoint solo se ejecuta cuando revisor_id todavía
    era NULL (su propio guard exige estado == pendiente_asignacion), así
    que nunca es una reasignación real — no hay "revisor anterior" que
    registrar.

    Los reasignos ocurridos ANTES de que este modelo existiera no
    aparecen en el timeline de la idea (GET /ideas/{id}/linea-tiempo) —
    ese dato ya se perdió, porque revision_ideas solo guardaba el
    revisor_id vigente, sobrescrito en cada reasignación anterior.
    """

    __tablename__ = "historial_reasignacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("revision_ideas.id"), nullable=False)
    revisor_anterior_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    revisor_nuevo_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    revision: Mapped["RevisionIdea"] = relationship()
    revisor_anterior: Mapped["Usuario"] = relationship(foreign_keys=[revisor_anterior_id])
    revisor_nuevo: Mapped["Usuario"] = relationship(foreign_keys=[revisor_nuevo_id])
