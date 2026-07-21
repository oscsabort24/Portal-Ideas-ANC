"""Validación de tokens de Microsoft Entra ID (Azure AD).

Verifica la firma del JWT contra las claves públicas del tenant (endpoint
JWKS), y que el token sea para esta app (audience) y no esté expirado.
Las claves públicas se cachean en memoria (rotan con poca frecuencia) para
no pegarle a Microsoft en cada request.
"""

import time

import httpx
from jose import jwt
from jose.exceptions import JWTError

from core.config import settings

JWKS_URL = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
JWKS_CACHE_TTL_SEGUNDOS = 3600

# Un token de Azure AD puede traer el issuer en formato v1 o v2 según el
# endpoint que lo emitió; se acepta cualquiera de los dos, siempre que sea
# del tenant configurado.
_ISSUER_V1 = f"https://sts.windows.net/{settings.azure_tenant_id}/"
_ISSUER_V2 = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0"

_jwks_cache: dict = {"keys": None, "obtenido_en": 0.0}


class AuthError(Exception):
    """Token inválido, expirado, de otra audiencia, o cualquier otro fallo de validación."""


def _obtener_jwks(forzar_refresh: bool = False) -> list[dict]:
    ahora = time.time()
    vencido = (ahora - _jwks_cache["obtenido_en"]) > JWKS_CACHE_TTL_SEGUNDOS
    if forzar_refresh or _jwks_cache["keys"] is None or vencido:
        try:
            respuesta = httpx.get(JWKS_URL, timeout=10)
            respuesta.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthError(f"No se pudieron obtener las claves públicas de Microsoft: {exc}") from exc
        _jwks_cache["keys"] = respuesta.json()["keys"]
        _jwks_cache["obtenido_en"] = ahora
    return _jwks_cache["keys"]


def _clave_para_kid(kid: str) -> dict:
    for clave in _obtener_jwks():
        if clave.get("kid") == kid:
            return clave
    # La clave puede no estar en caché por una rotación reciente de Microsoft
    # (poco frecuente) — se fuerza un refresh una única vez antes de fallar.
    for clave in _obtener_jwks(forzar_refresh=True):
        if clave.get("kid") == kid:
            return clave
    raise AuthError(f"No se encontró una clave pública de Microsoft con kid={kid}")


def validar_token_azure(token: str) -> dict:
    """Valida firma, audience y expiración de un token de Azure AD.

    Devuelve los claims del token (incluye 'oid' y, normalmente,
    'preferred_username' con el correo del usuario) si es válido.
    Lanza AuthError con un mensaje claro si no lo es.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthError("Token malformado") from exc

    kid = header.get("kid")
    if not kid:
        raise AuthError("El token no trae 'kid' en el header")

    clave = _clave_para_kid(kid)

    try:
        claims = jwt.decode(
            token,
            clave,
            algorithms=["RS256"],
            audience=settings.azure_api_audience,
            options={"verify_iss": False},  # el issuer se valida a mano abajo (v1 o v2)
        )
    except JWTError as exc:
        raise AuthError(f"Token inválido: {exc}") from exc

    if claims.get("iss") not in (_ISSUER_V1, _ISSUER_V2):
        raise AuthError("El token no fue emitido por el tenant esperado")

    return claims
