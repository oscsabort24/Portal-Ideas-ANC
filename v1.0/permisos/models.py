import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from usuarios.models import RolUsuario, Usuario  # noqa: F401 — necesario para resolver relationship


class ClavePermiso(str, enum.Enum):
    ve_todas_las_ideas = "ve_todas_las_ideas"
    ve_flow_control = "ve_flow_control"
    es_revisor_elegible = "es_revisor_elegible"
    corrige_clasificacion = "corrige_clasificacion"


class PermisoRol(Base):
    """Permiso configurable por rol — ver
    diseno-pendiente/fase-permisos-por-rol.md.preview (ya implementado).

    admin NUNCA tiene fila acá: es bypass hardcodeado en
    permisos/service.py:rol_tiene_permiso, a propósito — permitir que un
    admin se quite su propio acceso al panel que sirve para arreglar ese
    tipo de error sería un riesgo sin beneficio.
    """

    __tablename__ = "permisos_rol"
    __table_args__ = (UniqueConstraint("rol", "clave_permiso", name="uq_permiso_rol_clave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rol: Mapped[RolUsuario] = mapped_column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    clave_permiso: Mapped[ClavePermiso] = mapped_column(
        Enum(ClavePermiso, name="clave_permiso"), nullable=False
    )
    permitido: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # NULL = fila de seed, nunca editada por una persona todavía — mismo
    # criterio que DocumentoCriterio.actualizado_por_id ya usaba.
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    actualizado_por: Mapped["Usuario | None"] = relationship()
