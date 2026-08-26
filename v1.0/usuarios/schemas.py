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

    # VALOR DE COMPATIBILIDAD — ya no se le pide al usuario.
    #
    # miembros_cab.tipo_cab es NOT NULL (usuarios/models.py:109) y no se puede
    # quitar sin una migración, pero dejó de ser el criterio de acceso cuando
    # se pasó a CAB-por-departamento: quién ve qué lo decide
    # miembros_cab_departamentos (ver comites/service.py:departamentos_visibles,
    # que ni siquiera lee esta columna). El formulario de alta ya no muestra el
    # dropdown, así que el default se aplica acá.
    #
    # Se reusa `innovacion` en vez de agregar un valor neutro ("no_aplica")
    # a propósito: TipoCAB es un enum COMPARTIDO con comite_ideas.tipo_cab, que
    # sí tiene significado en el flujo de clasificación. Sumarle un miembro
    # para uso exclusivo de esta tabla lo filtraría a un camino donde nadie lo
    # maneja. El precio es que el valor no es semánticamente neutro — por eso
    # la ficha ya no lo muestra como si alguien lo hubiera elegido.
    tipo_cab: TipoCAB = TipoCAB.innovacion

    # Alta en UN SOLO PASO: los departamentos que esta persona podrá ver se
    # mandan en el mismo POST. Antes el alta creaba la membresía sin filas en
    # miembros_cab_departamentos, y "sin filas" significa COMODÍN (ve todas las
    # ideas de todos los departamentos, ver departamentos_visibles) — o sea que
    # cada Portfolio Owner recién creado veía todo hasta que alguien se
    # acordara de editarlo en un segundo paso. Lista vacía sigue siendo válida
    # y sigue significando comodín, pero ahora es una elección explícita.
    departamento_ids: list[int] = []


class MiembroCABOut(BaseModel):
    """Ya NO hereda de MiembroCABCreate: desde que el alta acepta
    departamento_ids, heredar arrastraría ese campo de entrada a la
    respuesta, donde el alcance ya se expone —resuelto y con nombre— como
    `departamentos` en MiembroCABDetalleOut."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    tipo_cab: TipoCAB


class MiembroCABDetalleOut(MiembroCABOut):
    usuario: UsuarioOut
    departamentos: list[DepartamentoOut] = []


class ActualizarDepartamentosMiembroCABRequest(BaseModel):
    departamento_ids: list[int]
