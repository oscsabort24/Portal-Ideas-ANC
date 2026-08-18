from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from permisos import schemas
from permisos.models import ClavePermiso, PermisoRol
from permisos.service import invalidar_cache, permisos_efectivos, rol_tiene_permiso
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual, requerir_admin

router = APIRouter(prefix="/permisos-rol", tags=["permisos"])

# admin nunca aparece en la grilla — siempre tiene todo, no es configurable
# (ver permisos/service.py:rol_tiene_permiso).
ROLES_CONFIGURABLES = (
    usuarios_models.RolUsuario.colaborador,
    usuarios_models.RolUsuario.encargado_area,
    usuarios_models.RolUsuario.gerente,
)


@router.get("", response_model=list[schemas.PermisoRolOut])
def listar_permisos_rol(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    return db.query(PermisoRol).all()


@router.put("", response_model=list[schemas.PermisoRolOut])
def guardar_permisos_rol(
    payload: schemas.GuardarPermisosRequest,
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    for item in payload.permisos:
        if item.rol not in ROLES_CONFIGURABLES:
            raise HTTPException(status_code=400, detail="admin no es un rol configurable en esta grilla")
        fila = db.query(PermisoRol).filter_by(rol=item.rol, clave_permiso=item.clave_permiso).first()
        if fila is None:
            fila = PermisoRol(rol=item.rol, clave_permiso=item.clave_permiso)
            db.add(fila)
        fila.permitido = item.permitido
        fila.actualizado_por_id = admin.id

    db.commit()
    invalidar_cache()
    return db.query(PermisoRol).all()


# Router sin prefijo /permisos-rol: endpoints de lectura para cualquier
# usuario autenticado (no solo admin), consumidos por el frontend para
# decidir qué mostrar sin exponer la tabla cruda de configuración.
router_publico = APIRouter(tags=["permisos"])


@router_publico.get("/me/permisos")
def mis_permisos(
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    return permisos_efectivos(db, usuario_actual)


@router_publico.get("/permisos-rol/roles/{clave_permiso}")
def roles_con_permiso(
    clave_permiso: ClavePermiso,
    db: Session = Depends(get_db),
    _usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    """Qué roles tienen este permiso — usado por el frontend para armar
    selectores de "a quién puedo asignar" (ej. picker de revisor) sin
    tener que hardcodear la lista de roles en el cliente."""
    return [rol.value for rol in usuarios_models.RolUsuario if rol_tiene_permiso(db, rol, clave_permiso)]
