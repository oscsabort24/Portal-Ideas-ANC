from datetime import datetime

from pydantic import BaseModel, ConfigDict

from documentos.models import TipoDocumento


class DocumentoGeneradoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    tipo_documento: TipoDocumento
    contenido: dict
    generado_en: datetime


class DescargarZipRequest(BaseModel):
    tipos: list[TipoDocumento]
