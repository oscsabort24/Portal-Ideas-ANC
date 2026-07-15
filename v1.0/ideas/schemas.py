from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ideas.models import EstadoIdea, RolMensaje


class IdeaCreate(BaseModel):
    titulo: str
    autor_id: int


class MensajeEntrevistaCreate(BaseModel):
    contenido: str


class MensajeEntrevistaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rol: RolMensaje
    contenido: str
    orden: int
    creado_en: datetime


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str | None
    estado: EstadoIdea
    autor_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_envio: datetime | None


class IdeaDetalleOut(IdeaOut):
    mensajes: list[MensajeEntrevistaOut]


class RespuestaEntrevistaOut(BaseModel):
    idea: IdeaOut
    mensaje_usuario: MensajeEntrevistaOut
    mensaje_asistente: MensajeEntrevistaOut


class EventoLineaTiempoOut(BaseModel):
    tipo: str
    descripcion: str
    fecha: datetime
    color: Literal["exito", "advertencia", "peligro", "info"]
