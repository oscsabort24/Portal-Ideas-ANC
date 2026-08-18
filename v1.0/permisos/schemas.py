from pydantic import BaseModel, ConfigDict

from permisos.models import ClavePermiso
from usuarios.models import RolUsuario


class PermisoRolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rol: RolUsuario
    clave_permiso: ClavePermiso
    permitido: bool


class PermisoRolActualizar(BaseModel):
    rol: RolUsuario
    clave_permiso: ClavePermiso
    permitido: bool


class GuardarPermisosRequest(BaseModel):
    permisos: list[PermisoRolActualizar]
