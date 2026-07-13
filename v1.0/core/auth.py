"""Validación de tokens de Microsoft Entra ID — andamiaje, todavía sin implementar.

Pendiente de que IT (Arnoldo) provea Tenant ID, Client ID y Client Secret
de la app registrada en Azure AD. Ver README.md para el detalle de qué falta.
No usar en ningún endpoint hasta que esté implementado: hoy usuarios/dependencies.py
sigue con la verificación temporal por header X-Usuario-Id.
"""


def validar_token_azure(token: str) -> dict:
    raise NotImplementedError(
        "validar_token_azure no está implementado todavía: pendiente de credenciales "
        "de Azure AD (Tenant ID / Client ID / Client Secret) por parte de IT."
    )
