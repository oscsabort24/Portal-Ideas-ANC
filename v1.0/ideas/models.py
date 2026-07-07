import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from usuarios.models import Usuario  # noqa: F401 — necesario para resolver la relación Idea.autor


class EstadoIdea(str, enum.Enum):
    borrador = "borrador"
    enviada = "enviada"


class RolMensaje(str, enum.Enum):
    usuario = "usuario"
    asistente = "asistente"


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[EstadoIdea] = mapped_column(
        Enum(EstadoIdea, name="estado_idea"), default=EstadoIdea.borrador, nullable=False
    )

    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    autor: Mapped["Usuario"] = relationship()

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mensajes: Mapped[list["MensajeEntrevista"]] = relationship(
        back_populates="idea", order_by="MensajeEntrevista.orden"
    )


class MensajeEntrevista(Base):
    """Historial de la entrevista conversacional de una idea.

    `orden` se calcula explícitamente en el código de aplicación
    (MAX(orden) del historial + 1 dentro de la misma transacción),
    no se infiere de timestamps, para que quede robusto ante reintentos.
    """

    __tablename__ = "mensajes_entrevista"
    __table_args__ = (UniqueConstraint("idea_id", "orden", name="uq_mensaje_idea_orden"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    rol: Mapped[RolMensaje] = mapped_column(Enum(RolMensaje, name="rol_mensaje"), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship(back_populates="mensajes")
