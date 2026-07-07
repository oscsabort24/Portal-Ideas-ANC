from pydantic import BaseModel, ConfigDict, EmailStr

from usuarios.models import RolUsuario, TipoCAB


class DepartamentoBase(BaseModel):
    nombre: str


class DepartamentoCreate(DepartamentoBase):
    pass


class DepartamentoUpdate(BaseModel):
    nombre: str


class DepartamentoOut(DepartamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: RolUsuario = RolUsuario.colaborador
    departamento_id: int | None = None
    reporta_a_id: int | None = None


class UsuarioCreate(BaseModel):
    nombre: str
    correo: EmailStr
    departamento_id: int | None = None
    reporta_a_id: int | None = None


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    correo: EmailStr | None = None
    rol: RolUsuario | None = None
    departamento_id: int | None = None
    reporta_a_id: int | None = None
    activo: bool | None = None


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


class MiembroCABDetalleOut(MiembroCABOut):
    usuario: UsuarioOut
