import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from usuarios.models import Usuario  # noqa: F401 — necesario para resolver las relaciones a Usuario


class TipoCriterio(str, enum.Enum):
    clasificacion = "clasificacion"
    asignacion_revisor = "asignacion_revisor"


class DocumentoCriterio(Base):
    """Una versión de un documento de criterios de IA.

    Solo una versión por `tipo` tiene `activo=True` a la vez — es la que
    usa el módulo de IA y la que se sirve en /criterios/{tipo} y
    /criterios/{tipo}/descargar. Las versiones anteriores se conservan
    (activo=False) para el historial de auditoría, nunca se borran.
    """

    __tablename__ = "documentos_criterio"
    __table_args__ = (UniqueConstraint("tipo", "version", name="uq_documento_criterio_tipo_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[TipoCriterio] = mapped_column(Enum(TipoCriterio, name="tipo_criterio"), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(300), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    subido_por: Mapped["Usuario"] = relationship()
    subido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PinAdmin(Base):
    """PIN personal de cada admin, para autorizar el reemplazo de documentos de criterios.

    Un PIN por usuario (no compartido entre admins). Se guarda solo el hash
    (nunca el PIN en texto plano) — ver criterios/seguridad.py para el hashing.
    """

    __tablename__ = "pines_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    usuario: Mapped["Usuario"] = relationship()
