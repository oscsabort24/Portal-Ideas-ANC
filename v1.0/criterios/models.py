import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from usuarios.models import Departamento, Usuario  # noqa: F401 — necesario para resolver las relaciones


class TipoCriterio(str, enum.Enum):
    clasificacion = "clasificacion"
    asignacion_revisor = "asignacion_revisor"
    entrevista = "entrevista"


class CriterioIA(Base):
    """Texto editable que alimenta un prompt de IA, versionado y protegido
    por PIN de admin — reemplaza a DocumentoCriterio (documento subido).

    departamento_id es NULL siempre para 'clasificacion' y
    'asignacion_revisor' (criterios únicos, globales — validado en
    criterios/router.py, no en la base). Para 'entrevista', NULL significa
    "texto por defecto, aplica a los 18 departamentos salvo excepción", y
    un departamento_id real es la excepción de ESE departamento puntual.

    Cada guardado SIEMPRE crea una versión nueva y desactiva la anterior
    (máxima trazabilidad/auditoría) — no existe edición sin versionar.
    """

    __tablename__ = "criterios_ia"
    __table_args__ = (
        UniqueConstraint(
            "tipo", "departamento_id", "version", name="uq_criterio_ia_tipo_departamento_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[TipoCriterio] = mapped_column(Enum(TipoCriterio, name="tipo_criterio"), nullable=False)
    departamento_id: Mapped[int | None] = mapped_column(ForeignKey("departamentos.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contenido: Mapped[str] = mapped_column(Unicode(), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)

    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    departamento: Mapped["Departamento | None"] = relationship()
    creado_por: Mapped["Usuario"] = relationship()


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
