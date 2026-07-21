"""Identificación del usuario actual.

Prioriza un token real de Microsoft Entra ID (header 'Authorization: Bearer
{token}', validado contra Azure AD en core/auth.py). Si no viene ese header,
cae a X-Usuario-Id — ese fallback existe SOLO para desarrollo local sin
Azure AD configurado (modo simulado del frontend, ver frontend/src/core/api.ts);
en producción el frontend siempre manda Authorization real, así que esa rama
nunca se ejercita ahí.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.auth import AuthError, validar_token_azure
from core.database import get_db
from usuarios import models


def obtener_usuario_actual(
    authorization: str | None = Header(default=None),
    x_usuario_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Usuario:
    if authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Authorization debe ser 'Bearer {token}'")
        token = authorization.split(" ", 1)[1].strip()

        try:
            claims = validar_token_azure(token)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        # preferred_username es el claim estándar de Azure AD para el correo
        # de inicio de sesión; email/upn quedan de respaldo por si el tenant
        # no lo trae.
        correo = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
        if not correo:
            raise HTTPException(status_code=401, detail="El token no contiene un correo utilizable")

        # Misma búsqueda case-insensitive que GET /usuarios/por-correo.
        usuario = db.query(models.Usuario).filter(func.lower(models.Usuario.correo) == func.lower(correo)).first()
        if not usuario:
            raise HTTPException(status_code=401, detail="No existe un usuario registrado con ese correo")
        return usuario

    if x_usuario_id is not None:
        usuario = db.get(models.Usuario, x_usuario_id)
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return usuario

    raise HTTPException(status_code=401, detail="Falta autenticación: Authorization Bearer o X-Usuario-Id")


def requerir_admin(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
) -> models.Usuario:
    if usuario_actual.rol != models.RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Se requiere rol admin para esta acción")
    return usuario_actual
