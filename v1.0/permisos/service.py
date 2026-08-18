"""Caché en memoria de permisos_rol.

La tabla es minúscula (4 permisos x hasta 3 roles configurables) y se
edita con muy poca frecuencia (un admin configurando, no una ruta de alta
frecuencia) — se cachea entera en memoria del proceso y se invalida por
completo en cada guardado, en vez de invalidar fila por fila.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from permisos.models import ClavePermiso, PermisoRol
from usuarios.dependencies import obtener_usuario_actual
from usuarios.models import RolUsuario, Usuario

_cache: dict[tuple[RolUsuario, ClavePermiso], bool] | None = None


def invalidar_cache() -> None:
    global _cache
    _cache = None


def _cargar_cache(db: Session) -> dict[tuple[RolUsuario, ClavePermiso], bool]:
    global _cache
    if _cache is None:
        _cache = {(fila.rol, fila.clave_permiso): fila.permitido for fila in db.query(PermisoRol).all()}
    return _cache


def rol_tiene_permiso(db: Session, rol: RolUsuario, clave: ClavePermiso) -> bool:
    if rol == RolUsuario.admin:
        return True
    return _cargar_cache(db).get((rol, clave), False)


def tiene_permiso(db: Session, usuario: Usuario, clave: ClavePermiso) -> bool:
    return rol_tiene_permiso(db, usuario.rol, clave)


def permisos_efectivos(db: Session, usuario: Usuario) -> dict[str, bool]:
    """Para GET /me/permisos — booleanos resueltos, no la tabla cruda."""
    return {clave.value: rol_tiene_permiso(db, usuario.rol, clave) for clave in ClavePermiso}


def requerir_permiso(clave: ClavePermiso):
    def _verificar(
        usuario_actual: Usuario = Depends(obtener_usuario_actual),
        db: Session = Depends(get_db),
    ) -> Usuario:
        if not tiene_permiso(db, usuario_actual, clave):
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        return usuario_actual

    return _verificar
