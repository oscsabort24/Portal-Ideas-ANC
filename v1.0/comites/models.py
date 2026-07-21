import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from ideas.models import Idea  # noqa: F401 — necesario para resolver la relación ComiteIdea.idea
from usuarios.models import TipoCAB, Usuario  # noqa: F401 — necesario para resolver la relación .aprobada_o_rechazada_por


class EstadoComite(str, enum.Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"


class ComiteIdea(Base):
    """Paso de una idea clasificada por la cola del CAB correspondiente.

    Se crea automáticamente cuando un admin clasifica la idea (ver
    comites/service.py:crear_comite_idea_para_idea, llamado desde
    clasificacion/router.py:clasificar). `tipo_cab` se copia de la
    clasificación al momento de crearse, para no depender de un join
    extra después.

    El orden de llegada a la cola es simplemente `creado_en` (+ `id`
    como desempate) — no hay un contador explícito porque cada fila se
    crea una sola vez desde un único punto de integración, sin riesgo
    real de carrera.

    El estado final "aprobada_por_cab" vive únicamente en `estado` de
    este modelo — no se refleja en Idea.estado, que describe solo la
    etapa de captura (borrador/enviada).
    """

    __tablename__ = "comite_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), unique=True, nullable=False)
    tipo_cab: Mapped[TipoCAB] = mapped_column(Enum(TipoCAB, name="tipo_cab_comite"), nullable=False)
    estado: Mapped[EstadoComite] = mapped_column(Enum(EstadoComite, name="estado_comite"), nullable=False)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    aprobada_o_rechazada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    aprobada_o_rechazada_por: Mapped["Usuario | None"] = relationship()
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    idea: Mapped["Idea"] = relationship()


class PresupuestoRango(str, enum.Enum):
    cero = "0"
    hasta_10000 = "1-10000"
    hasta_20000 = "10001-20000"
    hasta_30000 = "20001-30000"
    mas_30000 = "+30000"


class NivelImpactoConfianza(str, enum.Enum):
    muy_bajo = "muy_bajo"
    medio = "medio"
    alto = "alto"
    muy_alto = "muy_alto"


class NivelEsfuerzo(str, enum.Enum):
    corto_plazo = "corto_plazo"
    medio_plazo = "medio_plazo"
    largo_plazo = "largo_plazo"


class PrioridadRice(str, enum.Enum):
    baja = "baja"
    media = "media"
    alta = "alta"


class RiceEvaluacion(Base):
    """Evaluación RICE de una idea, llenada OPCIONALMENTE por quien la
    evalúa en el comité (CAB) — ver comites/router.py. 1:1 con
    ComiteIdea (no con Idea): quien la llena es el evaluador del comité,
    no parte del proceso de captura de la idea. Nunca bloquea aprobar ni
    rechazar.

    `calificacion` y `prioridad` SIEMPRE se recalculan en el backend a
    partir de los demás campos (ver comites/rice.py:calcular_calificacion)
    — nunca se confía en un valor que venga del cliente, ni siquiera en
    un PUT que reemplaza toda la evaluación.
    """

    __tablename__ = "rice_evaluaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comite_idea_id: Mapped[int] = mapped_column(ForeignKey("comite_ideas.id"), unique=True, nullable=False)

    area: Mapped[str] = mapped_column(String(200), nullable=False)
    lider_funcional: Mapped[str] = mapped_column(String(200), nullable=False)
    paises: Mapped[int] = mapped_column(Integer, nullable=False)
    presupuesto_rango: Mapped[PresupuestoRango] = mapped_column(
        Enum(PresupuestoRango, name="presupuesto_rango"), nullable=False
    )
    impacta_plan_estrategico: Mapped[bool] = mapped_column(Boolean, nullable=False)
    alcance_departamentos: Mapped[int] = mapped_column(Integer, nullable=False)
    impacto: Mapped[NivelImpactoConfianza] = mapped_column(
        Enum(NivelImpactoConfianza, name="rice_impacto"), nullable=False
    )
    confianza: Mapped[NivelImpactoConfianza] = mapped_column(
        Enum(NivelImpactoConfianza, name="rice_confianza"), nullable=False
    )
    esfuerzo: Mapped[NivelEsfuerzo] = mapped_column(Enum(NivelEsfuerzo, name="rice_esfuerzo"), nullable=False)

    calificacion: Mapped[float] = mapped_column(Float, nullable=False)
    prioridad: Mapped[PrioridadRice] = mapped_column(Enum(PrioridadRice, name="prioridad_rice"), nullable=False)

    completado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    completado_por: Mapped["Usuario"] = relationship()
    completado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    comite_idea: Mapped["ComiteIdea"] = relationship()
