from datetime import datetime

from pydantic import BaseModel, ConfigDict

from notificaciones.models import EtapaEscalamiento


class UsuarioResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class ConfiguracionEscalamientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    etapa: EtapaEscalamiento
    plazo_dias: int | None
    responsable_id: int | None
    responsable: UsuarioResumenOut | None
    actualizado_en: datetime


class ConfiguracionEscalamientoUpdate(BaseModel):
    plazo_dias: int | None = None
    responsable_id: int | None = None


class IdeaResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titulo: str


class NotificacionEscalamientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    etapa: EtapaEscalamiento
    idea_id: int
    idea: IdeaResumenOut
    responsable_id: int | None
    responsable: UsuarioResumenOut | None
    dias_transcurridos: int
    generada_en: datetime
    enviada: bool


class RevisarResultadoOut(BaseModel):
    notificaciones_generadas: int
    notificaciones: list[NotificacionEscalamientoOut]
