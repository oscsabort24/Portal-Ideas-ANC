from datetime import datetime

from pydantic import BaseModel, ConfigDict

from clasificacion.models import EstadoClasificacion
from ideas.schemas import IdeaOut
from usuarios.models import TipoCAB


class UsuarioResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class ClasificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    estado: EstadoClasificacion
    clasificacion: TipoCAB | None
    clasificado_por_id: int | None
    fecha_clasificacion: datetime | None
    creado_en: datetime


class ClasificacionDetalleOut(ClasificacionOut):
    idea: IdeaOut
    clasificado_por: UsuarioResumenOut | None


class ClasificarRequest(BaseModel):
    clasificacion: TipoCAB
