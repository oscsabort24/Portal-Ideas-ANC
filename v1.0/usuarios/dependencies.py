"""Verificación de rol TEMPORAL, mientras no exista autenticación real (login Entra ID).

Identifica al usuario actual por el header X-Usuario-Id (enviado por el frontend
desde UsuarioActualContext). No valida ninguna credencial — cualquiera que conozca
un id de usuario admin puede enviarlo. Reemplazar por autenticación real (JWT/sesión
de Entra ID) antes de ir a producción.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.auth import AuthError, validar_token_azure
from core.database import get_db
from usuarios import models


def obtener_usuario_actual_seguro(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Identifica al usuario actual por un token real de Microsoft Entra ID
    (header 'Authorization: Bearer {token}'), a diferencia de
    obtener_usuario_actual (X-Usuario-Id, temporal mientras no había login real).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el header Authorization: Bearer {token}")
    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = validar_token_azure(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # preferred_username es el claim estándar de Azure AD para el correo de
    # inicio de sesión; email/upn quedan de respaldo por si el tenant no lo trae.
    correo = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
    if not correo:
        raise HTTPException(status_code=401, detail="El token no contiene un correo utilizable")

    # Misma búsqueda case-insensitive que GET /usuarios/por-correo.
    usuario = db.query(models.Usuario).filter(func.lower(models.Usuario.correo) == func.lower(correo)).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="No existe un usuario registrado con ese correo")
    return usuario


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
