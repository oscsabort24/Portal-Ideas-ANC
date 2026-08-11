import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Unicode, UniqueConstraint
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
    nombre_archivo: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Texto editable del criterio (precargado desde el .docx al subir, ver
    # criterios/router.py:subir_documento) y explicación corta de para qué
    # sirve — ambos editables inline vía PATCH /criterios/{id} SIN generar
    # una versión nueva (a diferencia de subir_documento): una edición de
    # texto es una corrección sobre la MISMA versión activa, no un
    # reemplazo de documento. actualizado_por/actualizado_en solo se llenan
    # si hubo al menos una edición inline (quedan NULL si nunca se tocó).
    contenido: Mapped[str | None] = mapped_column(Unicode(), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actualizado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[actualizado_por_id])

    subido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    subido_por: Mapped["Usuario"] = relationship(foreign_keys=[subido_por_id])
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
    pin_hash: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Bloqueo temporal por intentos fallidos consecutivos al cambiar el PIN.
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Límite de cambios EXITOSOS de PIN por día calendario (no cuenta la creación inicial).
    cambios_hoy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fecha_ultimo_cambio: Mapped[date | None] = mapped_column(Date, nullable=True)

    usuario: Mapped["Usuario"] = relationship()
