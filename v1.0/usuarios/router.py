from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from usuarios import models, schemas

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[schemas.UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.post("", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(payload: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    usuario = models.Usuario(**payload.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/departamentos/", response_model=list[schemas.DepartamentoOut])
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(models.Departamento).all()


@router.post("/departamentos/", response_model=schemas.DepartamentoOut, status_code=201)
def crear_departamento(payload: schemas.DepartamentoCreate, db: Session = Depends(get_db)):
    departamento = models.Departamento(**payload.model_dump())
    db.add(departamento)
    db.commit()
    db.refresh(departamento)
    return departamento


@router.post("/cab/", response_model=schemas.MiembroCABOut, status_code=201)
def agregar_miembro_cab(payload: schemas.MiembroCABCreate, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, payload.usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    miembro = models.MiembroCAB(**payload.model_dump())
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro
