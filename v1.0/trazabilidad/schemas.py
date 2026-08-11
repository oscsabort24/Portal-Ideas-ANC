from datetime import datetime

from pydantic import BaseModel


class PersonaResumenOut(BaseModel):
    id: int
    nombre: str


class FlowControlIdeaOut(BaseModel):
    idea_id: int
    titulo: str
    estado_flow: str
    departamento_id: int | None
    departamento_nombre: str | None
    autor: PersonaResumenOut
    revisor: PersonaResumenOut | None
    miembros_comite: list[PersonaResumenOut] | None
    fecha_entrada_etapa: datetime
    dias_en_etapa: int
