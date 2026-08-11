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
    contenido: str | None = None
    descripcion: str | None = None
    subido_por: UsuarioResumenOut
    subido_en: datetime
    actualizado_por: UsuarioResumenOut | None = None
    actualizado_en: datetime | None = None


class DocumentoCriterioEditar(BaseModel):
    contenido: str | None = None
    descripcion: str | None = Field(default=None, max_length=500)
    pin: str
