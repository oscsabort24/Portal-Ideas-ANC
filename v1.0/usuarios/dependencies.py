"""Verificación de rol TEMPORAL, mientras no exista autenticación real (login Entra ID).

Identifica al usuario actual por el header X-Usuario-Id (enviado por el frontend
desde UsuarioActualContext). No valida ninguna credencial — cualquiera que conozca
un id de usuario admin puede enviarlo. Reemplazar por autenticación real (JWT/sesión
de Entra ID) antes de ir a producción.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from usuarios import models


def obtener_usuario_actual(
    x_usuario_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Usuario:
    if x_usuario_id is None:
        raise HTTPException(status_code=401, detail="Falta el header X-Usuario-Id")
    usuario = db.get(models.Usuario, x_usuario_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario


def requerir_admin(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
) -> models.Usuario:
    if usuario_actual.rol != models.RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Se requiere rol admin para esta acción")
    return usuario_actual
