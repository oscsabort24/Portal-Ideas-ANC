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
    aprobada_o_rechazada_por_id: int | None
    fecha_resolucion: datetime | None
    creado_en: datetime


class ComiteIdeaDetalleOut(ComiteIdeaOut):
    idea: IdeaOut
    aprobada_o_rechazada_por: UsuarioResumenOut | None


class RechazarRequest(BaseModel):
    motivo_rechazo: str = Field(min_length=1)


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
