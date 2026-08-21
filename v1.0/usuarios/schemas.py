from pydantic import BaseModel, ConfigDict, EmailStr

from usuarios.models import CompaniaUsuario, PaisUsuario, RolUsuario, TipoCAB


class DepartamentoBase(BaseModel):
    nombre: str


class DepartamentoCreate(DepartamentoBase):
    pass


class DepartamentoUpdate(BaseModel):
    nombre: str


class DepartamentoOut(DepartamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PuestoBase(BaseModel):
    nombre: str
    departamento_id: int


class PuestoCreate(PuestoBase):
    pass


class PuestoUpdate(BaseModel):
    nombre: str | None = None
    departamento_id: int | None = None


class PuestoUnicoUpdate(BaseModel):
    es_unico_por_pais: bool


class PuestoOut(PuestoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    es_unico_por_pais: bool


class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: RolUsuario = RolUsuario.colaborador
    pais: PaisUsuario
    compania: CompaniaUsuario
    departamento_id: int | None = None
    puesto_id: int | None = None
    reporta_a_id: int | None = None


class UsuarioCreate(BaseModel):
    nombre: str
    correo: EmailStr
    pais: PaisUsuario
    compania: CompaniaUsuario
    departamento_id: int | None = None
    puesto_id: int
    reporta_a_id: int | None = None


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    correo: EmailStr | None = None
    rol: RolUsuario | None = None
    pais: PaisUsuario | None = None
    compania: CompaniaUsuario | None = None
    departamento_id: int | None = None
    puesto_id: int | None = None
    reporta_a_id: int | None = None
    activo: bool | None = None


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool


class UsuarioBasicoOut(BaseModel):
    """Versión reducida de UsuarioOut para GET /usuarios/directorio-basico:
    sin correo ni rol — solo lo necesario para pickers de "elegí una
    persona" (onboarding, reasignación) sin exponer el directorio completo
    a cualquier identidad autenticada. Ver diagnóstico hallazgo #2."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    departamento_id: int | None = None


class MiembroCABCreate(BaseModel):
    usuario_id: int
    tipo_cab: TipoCAB


class MiembroCABOut(MiembroCABCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class MiembroCABDetalleOut(MiembroCABOut):
    usuario: UsuarioOut
    departamentos: list[DepartamentoOut] = []


class ActualizarDepartamentosMiembroCABRequest(BaseModel):
    departamento_ids: list[int]
