import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación DocumentoGenerado.idea


class TipoDocumento(str, enum.Enum):
    charter = "charter"
    bpmn = "bpmn"
    onepager = "onepager"
    raci = "raci"
    bmc = "bmc"
    business_case = "business_case"


class DocumentoGenerado(Base):
    """Uno de los 6 documentos formales generados al aprobar una idea por CAB.

    Se crean los 6 juntos, una sola vez, desde
    documentos/service.py:generar_documentos_para_idea — llamado desde
    comites/router.py:aprobar en la misma transacción. Son inmutables:
    no existe ningún endpoint que los regenere ni edite; la idea ya no
    admite cambios en esta etapa (coherente con que la única vía de
    edición es la rectificación en revision/, anterior a este punto).

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
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
