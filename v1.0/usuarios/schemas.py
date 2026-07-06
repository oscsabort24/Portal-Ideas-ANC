from pydantic import BaseModel, ConfigDict, EmailStr

from usuarios.models import RolUsuario, TipoCAB


class DepartamentoBase(BaseModel):
    nombre: str


class DepartamentoCreate(DepartamentoBase):
    pass


class DepartamentoOut(DepartamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: RolUsuario = RolUsuario.colaborador
    departamento_id: int | None = None
    reporta_a_id: int | None = None


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool


class MiembroCABCreate(BaseModel):
    usuario_id: int
    tipo_cab: TipoCAB


class MiembroCABOut(MiembroCABCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
