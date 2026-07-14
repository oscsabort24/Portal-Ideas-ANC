from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from criterios.models import TipoCriterio


class PinDefinir(BaseModel):
    pin_actual: str | None = None
    pin_nuevo: str = Field(min_length=4, max_length=6, pattern=r"^\d+$")


class UsuarioResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class DocumentoCriterioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: TipoCriterio
    nombre_archivo: str
    version: int
    activo: bool
    subido_por: UsuarioResumenOut
    subido_en: datetime
