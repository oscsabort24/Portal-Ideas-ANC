import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from core.reasignacion import MixinReasignacion
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación RevisionIdea.idea
from usuarios.models import Departamento, Usuario  # noqa: F401 — necesario para resolver las relaciones RevisionIdea.revisor / .departamento_sugerido_ia


class EstadoRevision(str, enum.Enum):
    pendiente_asignacion = "pendiente_asignacion"
    pendiente_revision = "pendiente_revision"
    aprobada = "aprobada"
    cambios_solicitados = "cambios_solicitados"
    # Se propuso pasarle la revisión a otra persona y esa persona todavía no
    # respondió. OJO: en este estado `revisor_id` SIGUE siendo el revisor
    # original — la titularidad no se transfiere hasta la aceptación (ver
    # RevisionIdea.propuesto_a_id).
    pendiente_aceptacion_reasignacion = "pendiente_aceptacion_reasignacion"


class OrigenAsignacion(str, enum.Enum):
    """De dónde salió el revisor actual de una revisión.

    mapeo_area/fallback_departamento_autor se registran hoy con la misma
    lógica de siempre (departamento+rol) — NO implican que ResponsableArea
    (Fase 3) ya esté activa; ver revision/service.py:_buscar_encargado_activo.
    """

    mapeo_area = "mapeo_area"
    fallback_departamento_autor = "fallback_departamento_autor"
    manual = "manual"
    sin_asignar = "sin_asignar"


class RevisionIdea(Base, MixinReasignacion):
    """Revisión de una idea enviada, por un encargado_area.

    Se crea automáticamente cuando la idea pasa a estado "enviada"
    (ver revision/service.py:crear_revision_para_idea, llamado desde
    ideas/router.py). Una idea tiene una sola revisión activa (idea_id
    es único).

    Hereda de MixinReasignacion (core/reasignacion.py) las 4 columnas del
    ciclo propuesta -> aceptación/rechazo — compartidas con ComiteIdea.
    """

    __tablename__ = "revision_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)
    revisor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    estado: Mapped[EstadoRevision] = mapped_column(
        Enum(EstadoRevision, name="estado_revision"), nullable=False
    )
    retroalimentacion: Mapped[str | None] = mapped_column(Unicode(), nullable=True)
    fecha_asignacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    departamento_sugerido_ia_id: Mapped[int | None] = mapped_column(
        ForeignKey("departamentos.id"), nullable=True
    )
    departamento_sugerido_ia: Mapped["Departamento | None"] = relationship()
    justificacion_ia: Mapped[str | None] = mapped_column(Unicode(), nullable=True)
    acepto_sugerencia_autor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Cómo se llegó al revisor_id actual (ver revision/service.py). NOT
    # NULL — el backfill de la migración b4d17c9e5a20 clasificó las filas
    # existentes; de acá en adelante todo alta lo declara explícito.
    origen_asignacion: Mapped[OrigenAsignacion] = mapped_column(
        Enum(OrigenAsignacion, name="origen_asignacion"), nullable=False
    )

    # Rechazos CONSECUTIVOS heredados del mixin, pero el criterio de "sale
    # del pool" (revisor_id=None, estado=pendiente_asignacion) es propio
    # de RevisionIdea — ComiteIdea lo maneja distinto (ver core/reasignacion.py).

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()
    # foreign_keys explícito: desde que existen propuesto_a_id y
    # reasignacion_solicitada_por_id (del mixin) hay varios caminos de FK
    # a `usuarios` y SQLAlchemy no puede elegir solo.
    revisor: Mapped["Usuario | None"] = relationship(foreign_keys=[revisor_id])


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
    retroalimentacion: Mapped[str] = mapped_column(Unicode(), nullable=False)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    revision: Mapped["RevisionIdea"] = relationship()
    creada_por: Mapped["Usuario"] = relationship()


class HistorialReasignacion(Base):
    """OBSOLETA — de solo lectura desde la migración c9f3e820d114.

    Sus filas se copiaron a ideas.models:HistorialIdea como eventos
    `reasignacion_aceptada`. Se conserva como respaldo del backfill; NO
    debe recibir filas nuevas — revision/router.py:reasignar ya escribe
    solo en HistorialIdea.
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
