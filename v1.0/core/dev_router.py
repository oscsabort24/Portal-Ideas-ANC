"""Accesos rápidos de desarrollo — SOLO se registra si settings.entorno == "development"
(ver main.py). No reemplaza el flujo real de MSAL, no emite tokens: reutiliza usuarios
reales de la BD para poder previsualizar cada rol de punta a punta sin pasar por Azure AD.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from usuarios import models, schemas

router = APIRouter(prefix="/auth", tags=["dev"])


class DevLoginRequest(BaseModel):
    correo: str


@router.post("/dev-login", response_model=schemas.UsuarioOut)
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    usuario = (
        db.query(models.Usuario)
        .filter(func.lower(models.Usuario.correo) == func.lower(payload.correo))
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese correo")
    return usuario
