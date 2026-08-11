from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from core.claude_client import EstadoBloque
from ideas.models import EstadoIdea, OrigenPregunta, RolMensaje


class IdeaCreate(BaseModel):
    # Sin autor_id a propósito: el autor se deriva del token en
    # ideas/router.py:crear_idea, no se acepta del cliente.
    titulo: str


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


class ProgresoBloquesOut(BaseModel):
    problema_alcance: EstadoBloque
    objetivo_medible: EstadoBloque
    beneficios: EstadoBloque
    entregables: EstadoBloque
    riesgos: EstadoBloque


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
    progreso_bloques: ProgresoBloquesOut | None


class IdeaDetalleOut(IdeaOut):
    mensajes: list[MensajeEntrevistaOut]


class RespuestaEntrevistaOut(BaseModel):
    idea: IdeaOut
    mensaje_usuario: MensajeEntrevistaOut
    mensaje_asistente: MensajeEntrevistaOut
    # Respuestas sugeridas para el turno actual (ver
    # core/claude_client.py:RespuestaEntrevista.options) — el frontend las
    # pinta como botones para que la persona no tenga que escribir montos,
    # plazos o países a mano.
    #
    # EFÍMERO a propósito: no se persiste en MensajeEntrevista, así que si
    # la persona recarga la página los botones del último turno no vuelven
    # (el campo de texto sigue funcionando igual, no se pierde nada del
    # avance). Persistirlo exigiría una columna nueva + migración; se
    # decidió no pagar eso todavía. Ver también GET /ideas/{id}, que por
    # eso mismo no devuelve `opciones`.
    opciones: list[str] | None = None


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
    origen: OrigenPregunta


class RespuestaPreguntaOut(BaseModel):
    respuesta: str
