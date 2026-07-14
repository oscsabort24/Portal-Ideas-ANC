from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ideas.schemas import IdeaOut
from revision.models import EstadoRevision


class UsuarioResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class RevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    revisor_id: int | None
    estado: EstadoRevision
    retroalimentacion: str | None
    fecha_asignacion: datetime | None
    fecha_resolucion: datetime | None


class RevisionDetalleOut(RevisionOut):
    idea: IdeaOut
    revisor: UsuarioResumenOut | None


class AsignarRequest(BaseModel):
    revisor_id: int


class ReasignarRequest(BaseModel):
    nuevo_revisor_id: int


class PedirCambiosRequest(BaseModel):
    retroalimentacion: str = Field(min_length=1)
