import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación NotificacionEscalamiento.idea
from usuarios.models import Usuario  # noqa: F401 — necesario para resolver las relaciones .responsable


class EtapaEscalamiento(str, enum.Enum):
    revision = "revision"
    clasificacion = "clasificacion"
    comites = "comites"


class ConfiguracionEscalamiento(Base):
    """Plazo y responsable de escalamiento por inactividad, por etapa.

    Una fila por etapa (etapa es unique). plazo_dias=NULL significa que
    la etapa está sin configurar / inactiva — POST /notificaciones/revisar
    la ignora. Las 3 filas se precargan por migración de datos con ambos
    campos en NULL (ver 20260714_seed_configuracion_escalamiento), para
    que el admin siempre encuentre las 3 etapas listas para configurar.
    """

    __tablename__ = "configuraciones_escalamiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etapa: Mapped[EtapaEscalamiento] = mapped_column(
        Enum(EtapaEscalamiento, name="etapa_escalamiento_config"), unique=True, nullable=False
    )
    plazo_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    responsable: Mapped["Usuario | None"] = relationship()


class NotificacionEscalamiento(Base):
    """Registro de una idea detectada como vencida en una etapa.

    Se crea desde POST /notificaciones/revisar. El envío de correo real
    queda como STUB: `enviada` empieza en False y hoy nada la pasa a
    True (no hay credenciales SMTP todavía) — el campo existe para que,
    cuando se conecte el envío real, quede claro qué notificaciones ya
    se procesaron.

    No hay unique constraint en (etapa, idea_id): para evitar duplicar
    el aviso en cada click de "Revisar vencidas ahora", el router
    verifica con un EXISTS que no haya ya una notificación previa para
    esa (etapa, idea_id) antes de crear una nueva — ver
    notificaciones/router.py:revisar. Si la idea avanza de etapa y
    vuelve a vencerse en la nueva etapa, sí genera una notificación
    distinta porque la etapa es parte de la clave de "ya avisado".
    """

    __tablename__ = "notificaciones_escalamiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etapa: Mapped[EtapaEscalamiento] = mapped_column(
        Enum(EtapaEscalamiento, name="etapa_escalamiento_notificacion"), nullable=False
    )
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    dias_transcurridos: Mapped[int] = mapped_column(Integer, nullable=False)
    generada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    enviada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    idea: Mapped["Idea"] = relationship()
    responsable: Mapped["Usuario | None"] = relationship()
