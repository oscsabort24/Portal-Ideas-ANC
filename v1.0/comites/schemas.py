from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from comites.models import EstadoComite, NivelEsfuerzo, NivelImpactoConfianza, PresupuestoRango, PrioridadRice
from ideas.schemas import IdeaOut
from usuarios.models import TipoCAB


class UsuarioResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class ComiteIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    tipo_cab: TipoCAB
    estado: EstadoComite
    motivo_rechazo: str | None
    asignado_a_id: int | None
    aprobada_o_rechazada_por_id: int | None
    fecha_resolucion: datetime | None
    creado_en: datetime

    # Ciclo de reasignación (ver core/reasignacion.py) — el frontend usa
    # propuesto_a_id + estado para mostrar el banner de aceptar/rechazar.
    propuesto_a_id: int | None
    reasignacion_solicitada_por_id: int | None
    fecha_solicitud_reasignacion: datetime | None


class ComiteIdeaDetalleOut(ComiteIdeaOut):
    idea: IdeaOut
    asignado_a: UsuarioResumenOut | None
    aprobada_o_rechazada_por: UsuarioResumenOut | None
    propuesto_a: UsuarioResumenOut | None
    reasignacion_solicitada_por: UsuarioResumenOut | None


class RechazarRequest(BaseModel):
    motivo_rechazo: str = Field(min_length=1)


class ReasignarComiteRequest(BaseModel):
    nuevo_asignado_id: int
    motivo: str | None = None


class RechazarReasignacionComiteRequest(BaseModel):
    motivo: str = Field(min_length=1)


class DepartamentoVisibleOut(BaseModel):
    id: int
    nombre: str


class RiceEvaluacionRequest(BaseModel):
    """calificacion y prioridad NO se aceptan acá — se recalculan siempre
    en el backend (ver comites/rice.py)."""

    area: str = Field(min_length=1)
    lider_funcional: str = Field(min_length=1)
    paises: int = Field(ge=0)
    presupuesto_rango: PresupuestoRango
    impacta_plan_estrategico: bool
    alcance_departamentos: int = Field(ge=0)
    impacto: NivelImpactoConfianza
    confianza: NivelImpactoConfianza
    esfuerzo: NivelEsfuerzo


class RiceEvaluacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comite_idea_id: int
    area: str
    lider_funcional: str
    paises: int
    presupuesto_rango: PresupuestoRango
    impacta_plan_estrategico: bool
    alcance_departamentos: int
    impacto: NivelImpactoConfianza
    confianza: NivelImpactoConfianza
    esfuerzo: NivelEsfuerzo
    calificacion: float
    prioridad: PrioridadRice
    completado_por_id: int
    completado_en: datetime
