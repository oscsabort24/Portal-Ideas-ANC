"""Identificación del usuario actual.

Prioriza un token real de Microsoft Entra ID (header 'Authorization: Bearer
{token}', validado contra Azure AD en core/auth.py). Si no viene ese header,
cae a X-Usuario-Id — ese fallback existe SOLO para desarrollo local sin
Azure AD configurado (modo simulado del frontend, ver frontend/src/core/api.ts).

Ese fallback está gateado por settings.entorno == "development", igual que
/auth/dev-login (ver main.py). El gate NO es opcional: mandar X-Usuario-Id no
requiere credencial alguna, así que sin él cualquiera puede actuar como
cualquier usuario —incluido un admin— con solo adivinar un id entero. Antes
se confiaba en que "el frontend en producción siempre manda Authorization
real", pero eso describe al cliente legítimo, no a un atacante: quien ataca no
usa nuestro frontend, hace la request a mano.

Hay DOS dependencias de autenticación, y la diferencia importa:

- obtener_identidad_autenticada: exige credenciales válidas, pero NO exige
  que exista una fila en `usuarios`. Es la que necesita el onboarding: una
  persona que acaba de entrar con Microsoft por primera vez tiene token
  válido y todavía no tiene Usuario. Si el onboarding usara
  obtener_usuario_actual quedaría en un bloqueo circular permanente (no
  puede crear su usuario porque no tiene usuario).

- obtener_usuario_actual: exige además que la identidad corresponda a un
  Usuario registrado. Es la dependencia por defecto para todo lo demás.
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.auth import AuthError, validar_token_azure
from core.config import settings
from core.database import get_db
from usuarios import models

logger = logging.getLogger("uvicorn.error")


@dataclass
class IdentidadAutenticada:
    """Quién hizo la request, tenga o no fila en `usuarios`.

    `usuario` es None solo en el caso de onboarding (token válido de una
    cuenta del tenant que todavía no se registró). `correo` siempre viene
    lleno y es la fuente de verdad para decidir si alguien se está dando
    de alta a sí mismo o a un tercero.
    """

    correo: str
    usuario: models.Usuario | None


def obtener_identidad_autenticada(
    authorization: str | None = Header(default=None),
    x_usuario_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> IdentidadAutenticada:
    if authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Authorization debe ser 'Bearer {token}'")
        token = authorization.split(" ", 1)[1].strip()

        try:
            claims = validar_token_azure(token)
        except AuthError as exc:
            # El motivo exacto (firma inválida / expirado / audience incorrecta)
            # va SOLO al log del operador. Devolvérselo al cliente convierte
            # este 401 en un oráculo: un atacante no autenticado puede sondear
            # la validación y aprender por qué falla cada token que prueba.
            logger.warning("Token de Azure rechazado: %s", exc)
            raise HTTPException(status_code=401, detail="Token inválido") from exc

        # preferred_username es el claim estándar de Azure AD para el correo
        # de inicio de sesión; email/upn quedan de respaldo por si el tenant
        # no lo trae.
        correo = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
        if not correo:
            raise HTTPException(status_code=401, detail="El token no contiene un correo utilizable")

        # Misma búsqueda case-insensitive que GET /usuarios/por-correo.
        usuario = (
            db.query(models.Usuario)
            .filter(func.lower(models.Usuario.correo) == func.lower(correo))
            .first()
        )
        return IdentidadAutenticada(correo=correo, usuario=usuario)

    # Mismo gate que /auth/dev-login (main.py): fuera de development se ignora
    # el header por completo y se responde igual que si no hubiera venido, para
    # no revelar que este fallback existe.
    if x_usuario_id is not None and settings.entorno == "development":
        usuario = db.get(models.Usuario, x_usuario_id)
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return IdentidadAutenticada(correo=usuario.correo, usuario=usuario)

    raise HTTPException(status_code=401, detail="Falta autenticación: Authorization Bearer")


def obtener_usuario_actual(
    identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
) -> models.Usuario:
    if identidad.usuario is None:
        raise HTTPException(status_code=401, detail="No existe un usuario registrado con ese correo")
    return identidad.usuario


def requerir_admin(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
) -> models.Usuario:
    if usuario_actual.rol != models.RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Se requiere rol admin para esta acción")
    return usuario_actual


def requerir_ve_flow_control(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> models.Usuario:
    # Antes era "admin o gerente" hardcodeado; ahora consulta el permiso
    # configurable ve_flow_control (ver permisos/, admin sigue siendo
    # bypass hardcodeado dentro de tiene_permiso). Import local para
    # evitar un ciclo: permisos/service.py también importa de este módulo.
    from permisos.models import ClavePermiso
    from permisos.service import tiene_permiso

    if not tiene_permiso(db, usuario_actual, ClavePermiso.ve_flow_control):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver Flow Control")
    return usuario_actual
