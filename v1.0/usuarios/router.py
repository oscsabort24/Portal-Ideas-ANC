from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from usuarios import models, schemas
from usuarios.dependencies import requerir_admin

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


@router.patch("/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/cab/{miembro_id}", status_code=204)
def quitar_miembro_cab(
    miembro_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    miembro = db.get(models.MiembroCAB, miembro_id)
    if not miembro:
        raise HTTPException(status_code=404, detail="Membresía de CAB no encontrada")
    db.delete(miembro)
    db.commit()


@router.patch("/departamentos/{departamento_id}", response_model=schemas.DepartamentoOut)
def actualizar_departamento(
    departamento_id: int,
    payload: schemas.DepartamentoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    departamento = db.get(models.Departamento, departamento_id)
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    departamento.nombre = payload.nombre
    db.commit()
    db.refresh(departamento)
    return departamento


@router.delete("/departamentos/{departamento_id}", status_code=204)
def eliminar_departamento(
    departamento_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    departamento = db.get(models.Departamento, departamento_id)
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    cantidad_personas = (
        db.query(models.Usuario).filter(models.Usuario.departamento_id == departamento_id).count()
    )
    if cantidad_personas > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {cantidad_personas} persona(s) asignada(s) a este departamento",
        )
    db.delete(departamento)
    db.commit()


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


@router.get("/cab/", response_model=list[schemas.MiembroCABDetalleOut])
def listar_miembros_cab(db: Session = Depends(get_db)):
    return db.query(models.MiembroCAB).all()


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
