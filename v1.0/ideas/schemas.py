from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ideas.models import EstadoIdea, RolMensaje


class IdeaCreate(BaseModel):
    titulo: str
    autor_id: int


class MensajeEntrevistaCreate(BaseModel):
    contenido: str
    # Sugerencia OPCIONAL del autor de quién debería revisar la idea. Si se
    # omite (None) en un mensaje, NO borra un valor ya guardado en un
    # mensaje anterior — ver ideas/router.py:enviar_mensaje.
    sugerencia_revisor_autor: str | None = None
    motivo_sugerencia_revisor_autor: str | None = None


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
    sugerencia_revisor_autor: str | None
    motivo_sugerencia_revisor_autor: str | None
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


class ResumenIdeaOut(BaseModel):
    resumen: str
    categoria_riesgo: str | None = None


class PreguntarRequest(BaseModel):
    pregunta: str


class RespuestaPreguntaOut(BaseModel):
    respuesta: str
