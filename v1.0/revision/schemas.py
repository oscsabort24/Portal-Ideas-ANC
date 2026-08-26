from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.rechazo import MIN_MOTIVO_RECHAZO

from ideas.models import TipoEventoIdea
from ideas.schemas import IdeaOut
from revision.models import EstadoRevision, OrigenAsignacion


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
    motivo_rechazo: str | None
    fecha_asignacion: datetime | None
    fecha_resolucion: datetime | None
    departamento_sugerido_ia_id: int | None
    justificacion_ia: str | None
    acepto_sugerencia_autor: bool | None
    origen_asignacion: OrigenAsignacion

    # Con propuesto_a_id != null y estado == pendiente_aceptacion_reasignacion,
    # el frontend sabe que esta fila requiere respuesta de quien la recibe
    # (badge "requiere tu respuesta" en Mis revisiones).
    propuesto_a_id: int | None
    reasignacion_solicitada_por_id: int | None
    fecha_solicitud_reasignacion: datetime | None


class RevisionDetalleOut(RevisionOut):
    idea: IdeaOut
    revisor: UsuarioResumenOut | None
    propuesto_a: UsuarioResumenOut | None
    reasignacion_solicitada_por: UsuarioResumenOut | None


class AsignarRequest(BaseModel):
    revisor_id: int


class ReasignarRequest(BaseModel):
    nuevo_revisor_id: int
    motivo: str | None = None


class RechazarReasignacionRequest(BaseModel):
    motivo: str = Field(min_length=1)


class HistorialIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    tipo_evento: TipoEventoIdea
    actor_id: int
    actor: UsuarioResumenOut
    sujeto_id: int | None
    sujeto: UsuarioResumenOut | None
    detalle: str | None
    creado_en: datetime


class PedirCambiosRequest(BaseModel):
    retroalimentacion: str = Field(min_length=1)


class RechazarRequest(BaseModel):
    # 20 caracteres: un rechazo cierra la idea de forma FINAL (no se reabre ni
    # se apela, ver revision/models.py:EstadoRevision.rechazada) y este texto
    # es lo único que el autor va a recibir como explicación. "No aplica" o
    # "no" pasaban el min_length=1 anterior.
    #
    # Se valida contra el texto YA recortado en el router, no solo acá: 20
    # espacios cumplen min_length pero no explican nada.
    motivo_rechazo: str = Field(min_length=MIN_MOTIVO_RECHAZO)


class HistorialRetroalimentacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    retroalimentacion: str
    creada_por_id: int
    creada_por: UsuarioResumenOut
    creada_en: datetime
