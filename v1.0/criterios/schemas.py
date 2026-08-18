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


class CriterioIAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: TipoCriterio
    departamento_id: int | None
    version: int
    activo: bool
    contenido: str
    descripcion: str | None = None
    creado_por: UsuarioResumenOut
    creado_en: datetime


class GuardarCriterioRequest(BaseModel):
    contenido: str = Field(min_length=1)
    descripcion: str | None = Field(default=None, max_length=500)
    departamento_id: int | None = None
    pin: str


class CoberturaDepartamentoOut(BaseModel):
    departamento_id: int
    nombre: str
    tiene_excepcion: bool
