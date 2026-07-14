from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from comites.models import EstadoComite
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
