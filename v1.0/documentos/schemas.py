from datetime import datetime

from pydantic import BaseModel, ConfigDict

from documentos.models import TipoDocumento
from usuarios.models import RolUsuario


class DocumentoGeneradoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    tipo_documento: TipoDocumento
    contenido: dict
    generado_en: datetime


class DescargarZipRequest(BaseModel):
    tipos: list[TipoDocumento]


class GenerarDocumentosRequest(BaseModel):
    tipos: list[TipoDocumento]


class PendientesOut(BaseModel):
    generados: list[TipoDocumento]
    pendientes: list[TipoDocumento]
    puede_generar: bool
    documentos_desactualizados: bool
    tipos_permitidos_rol: list[TipoDocumento]


class PermisoDocumentoRolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rol: RolUsuario
    tipo_documento: TipoDocumento
    permitido: bool


class PermisoDocumentoRolUpdate(BaseModel):
    rol: RolUsuario
    tipo_documento: TipoDocumento
    permitido: bool
