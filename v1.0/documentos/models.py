import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación DocumentoGenerado.idea
from usuarios.models import RolUsuario


class TipoDocumento(str, enum.Enum):
    charter = "charter"
    bpmn = "bpmn"
    onepager = "onepager"
    raci = "raci"
    bmc = "bmc"
    business_case = "business_case"


class DocumentoGenerado(Base):
    """Uno de los 6 documentos formales de una idea, generado manualmente
    por el autor (ver documentos/router.py:generar y :_puede_generar).

    Mutable SOLO mientras la idea no haya llegado a comité (no existe fila
    en ComiteIdea para esta idea): el autor puede generar tipos nuevos y
    regenerar tipos que ya existían, sobreescribiendo esta misma fila
    (contenido/ruta_archivo/generado_en) — ver
    documentos/service.py:generar_documentos_para_tipos. En cuanto existe
    ComiteIdea, los documentos quedan CONGELADOS: ni el autor ni CAB pueden
    generar/regenerar más, solo ver/descargar lo que ya exista.

    `contenido` guarda el dict ya ensamblado (campos estructurales +
    narrativos) que se usó para generar el .docx, serializado como JSON,
    para poder mostrarlo en pantalla sin tener que parsear el archivo.
    """

    __tablename__ = "documentos_generados"
    __table_args__ = (
        UniqueConstraint("idea_id", "tipo_documento", name="uq_documento_idea_tipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        Enum(TipoDocumento, name="tipo_documento"), nullable=False
    )
    contenido: Mapped[str] = mapped_column(Unicode(), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()


class PermisoDocumentoRol(Base):
    """Qué tipos de documento puede GENERAR cada rol (configurable por admin,
    ver documentos/router.py:_tipos_permitidos_para_rol).

    Independiente de DocumentoGenerado: quitarle el permiso a un rol después
    no afecta documentos ya generados, solo bloquea generación/regeneración
    futura — ver _puede_generar_tipo() en el router.

    `admin` no tiene filas acá a propósito: igual que en _puede_generar(),
    admin siempre puede generar cualquier tipo, sin depender de configuración.
    """

    __tablename__ = "permisos_documentos_rol"
    __table_args__ = (
        UniqueConstraint("rol", "tipo_documento", name="uq_permiso_rol_tipo_documento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rol: Mapped[RolUsuario] = mapped_column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        Enum(TipoDocumento, name="tipo_documento"), nullable=False
    )
    permitido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
