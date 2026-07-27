import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Unicode, UniqueConstraint
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


class OrigenPregunta(str, enum.Enum):
    revision = "revision"
    comite = "comite"


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Unicode(), nullable=True)
    estado: Mapped[EstadoIdea] = mapped_column(
        Enum(EstadoIdea, name="estado_idea"), default=EstadoIdea.borrador, nullable=False
    )

    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    autor: Mapped["Usuario"] = relationship()

    # Sugerencia OPCIONAL del autor de a quién le gustaría que revisara la
    # idea — capturada en cualquier mensaje de la entrevista (ver
    # ideas/router.py:enviar_mensaje) y usada como contexto adicional por
    # asignar_revisor_ia() en revision/service.py. La IA la considera pero
    # no la sigue ciegamente.
    sugerencia_revisor_autor: Mapped[str | None] = mapped_column(Unicode(300), nullable=True)
    motivo_sugerencia_revisor_autor: Mapped[str | None] = mapped_column(Unicode(), nullable=True)

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Último progreso_bloques devuelto por la IA (ver core/claude_client.py:
    # ProgresoBloques) — estado de cada uno de los 5 bloques obligatorios de
    # la entrevista, para el checklist visual del frontend. Se sobrescribe
    # completo en cada turno (no hay merge parcial); None mientras la
    # entrevista no ha tenido ningún turno todavía.
    progreso_bloques: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
    contenido: Mapped[str] = mapped_column(Unicode(), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship(back_populates="mensajes")


class PreguntaIdea(Base):
    """Bitácora append-only de cada pregunta hecha sobre una idea vía
    POST /ideas/{id}/preguntar (ver ideas/router.py:preguntar) — mismo
    patrón que revision/models.py:HistorialRetroalimentacion, nunca se
    edita ni se borra.

    FK directo a `ideas.id` (no a `revision_ideas.id`) porque estas
    preguntas se leen también desde CAB, que no tiene fila propia en
    revision_ideas — ver ideas/router.py:obtener_resumen, que anexa las de
    origen="revision" al resumen que ve el comité. Las de origen="comite"
    se guardan igual (para no perder el dato a futuro) pero nunca se
    reinyectan en ningún resumen, para no crear un bucle de contexto que
    crezca indefinidamente.
    """

    __tablename__ = "preguntas_idea"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    origen: Mapped[OrigenPregunta] = mapped_column(Enum(OrigenPregunta, name="origen_pregunta"), nullable=False)
    pregunta: Mapped[str] = mapped_column(Unicode(), nullable=False)
    respuesta: Mapped[str] = mapped_column(Unicode(), nullable=False)
    preguntada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
    preguntada_por: Mapped["Usuario"] = relationship()
