from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from usuarios import models, schemas
from usuarios.dependencies import (
    IdentidadAutenticada,
    obtener_identidad_autenticada,
    obtener_usuario_actual,
    requerir_admin,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _validar_puesto_unico(
    db: Session,
    puesto: models.Puesto,
    pais: models.PaisUsuario,
    excluir_usuario_id: int | None = None,
) -> None:
    """Si el puesto es único por país, rechaza si ya hay otra persona activa con ese puesto en ese país."""
    if not puesto.es_unico_por_pais:
        return
    query = db.query(models.Usuario).filter(
        models.Usuario.puesto_id == puesto.id,
        models.Usuario.pais == pais,
        models.Usuario.activo == True,  # noqa: E712
    )
    if excluir_usuario_id is not None:
        query = query.filter(models.Usuario.id != excluir_usuario_id)
    conflicto = query.first()
    if conflicto:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El puesto '{puesto.nombre}' ya está asignado a {conflicto.nombre} en {pais.value}. "
                "Es un puesto único por país."
            ),
        )


@router.get("", response_model=list[schemas.UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    _identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
):
    # Identidad y no usuario registrado: el onboarding llama a este endpoint
    # para llenar el selector "Reporta a" ANTES de que exista el Usuario de
    # quien lo está llenando (ver OnboardingPerfil.tsx).
    return db.query(models.Usuario).all()


@router.get("/por-correo", response_model=schemas.UsuarioOut)
def obtener_usuario_por_correo(
    correo: str,
    db: Session = Depends(get_db),
    _identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
):
    """Busca un usuario por correo, case-insensitive.

    Usado por el flujo de onboarding tras login con Microsoft (MSAL): el
    correo del token de Azure puede variar en mayúsculas respecto al
    guardado en nuestra BD. La collation real de la BD (SQL_Latin1_General_CP1_CI_AS)
    ya es case-insensitive, pero se normaliza con func.lower() en ambos
    lados explícitamente para no depender de ese detalle de configuración.
    404 es la señal que usa el frontend para decidir mostrar onboarding.
    Debe declararse ANTES de /{usuario_id} para que "por-correo" no se
    intente interpretar como un usuario_id numérico.
    """
    usuario = db.query(models.Usuario).filter(func.lower(models.Usuario.correo) == func.lower(correo)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese correo")
    return usuario


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
):
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.post("", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(
    payload: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
):
    """Alta de una persona. Dos llamadores legítimos, dos permisos distintos:

    - Onboarding (OnboardingPerfil.tsx): alguien con token válido del tenant
      que todavía no tiene fila en `usuarios` se da de alta A SÍ MISMO. Por
      eso la dependencia es la identidad y no el usuario registrado.
    - Admin (FormularioPersona.tsx): da de alta a terceros.

    Cualquier otro caso se rechaza: sin este guard, cualquiera con un token
    del tenant podría crear cuentas a nombre de otras personas. El rol nunca
    se acepta del payload (UsuarioCreate no lo expone) — toda alta nace como
    colaborador por el default del modelo, y solo un admin puede cambiarlo
    después vía PATCH /usuarios/{id}.
    """
    es_admin = identidad.usuario is not None and identidad.usuario.rol == models.RolUsuario.admin
    es_alta_propia = payload.correo.lower() == identidad.correo.lower()
    if not es_admin and not es_alta_propia:
        raise HTTPException(
            status_code=403,
            detail="Solo un admin puede dar de alta a otra persona",
        )

    puesto = db.get(models.Puesto, payload.puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    _validar_puesto_unico(db, puesto, payload.pais)

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

    cambios = payload.model_dump(exclude_unset=True)

    # Estado resultante tras aplicar el PATCH, para validar antes de guardar.
    puesto_id_resultante = cambios.get("puesto_id", usuario.puesto_id)
    pais_resultante = cambios.get("pais", usuario.pais)
    activo_resultante = cambios.get("activo", usuario.activo)

    if activo_resultante and puesto_id_resultante is not None:
        puesto = db.get(models.Puesto, puesto_id_resultante)
        if not puesto:
            raise HTTPException(status_code=404, detail="Puesto no encontrado")
        _validar_puesto_unico(db, puesto, pais_resultante, excluir_usuario_id=usuario.id)

    for campo, valor in cambios.items():
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
def listar_departamentos(
    db: Session = Depends(get_db),
    _identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
):
    # Identidad y no usuario registrado: el onboarding necesita el catálogo
    # de departamentos para poder elegir uno (ver OnboardingPerfil.tsx).
    return db.query(models.Departamento).all()


@router.post("/departamentos/", response_model=schemas.DepartamentoOut, status_code=201)
def crear_departamento(
    payload: schemas.DepartamentoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    departamento = models.Departamento(**payload.model_dump())
    db.add(departamento)
    db.commit()
    db.refresh(departamento)
    return departamento


@router.get("/puestos/", response_model=list[schemas.PuestoOut])
def listar_puestos(
    db: Session = Depends(get_db),
    _identidad: IdentidadAutenticada = Depends(obtener_identidad_autenticada),
):
    # Identidad y no usuario registrado: el onboarding necesita el catálogo
    # de puestos para poder elegir uno (ver OnboardingPerfil.tsx).
    return db.query(models.Puesto).all()


@router.post("/puestos/", response_model=schemas.PuestoOut, status_code=201)
def crear_puesto(
    payload: schemas.PuestoCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    departamento = db.get(models.Departamento, payload.departamento_id)
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    puesto = models.Puesto(**payload.model_dump())
    db.add(puesto)
    db.commit()
    db.refresh(puesto)
    return puesto


@router.patch("/puestos/{puesto_id}", response_model=schemas.PuestoOut)
def actualizar_puesto(
    puesto_id: int,
    payload: schemas.PuestoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.get(models.Puesto, puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    cambios = payload.model_dump(exclude_unset=True)
    if "departamento_id" in cambios and not db.get(models.Departamento, cambios["departamento_id"]):
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    for campo, valor in cambios.items():
        setattr(puesto, campo, valor)
    db.commit()
    db.refresh(puesto)
    return puesto


@router.patch("/puestos/{puesto_id}/unico", response_model=schemas.PuestoOut)
def actualizar_puesto_unico(
    puesto_id: int,
    payload: schemas.PuestoUnicoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.get(models.Puesto, puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")

    if payload.es_unico_por_pais:
        conteos = (
            db.query(models.Usuario.pais, func.count(models.Usuario.id))
            .filter(models.Usuario.puesto_id == puesto_id, models.Usuario.activo == True)  # noqa: E712
            .group_by(models.Usuario.pais)
            .having(func.count(models.Usuario.id) >= 2)
            .order_by(func.count(models.Usuario.id).desc())
            .all()
        )
        if conteos:
            pais, cantidad = conteos[0]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede marcar como único: ya hay {cantidad} persona(s) con este puesto en {pais.value}. "
                    "Reasigna o desactiva a las personas de más antes de continuar."
                ),
            )

    puesto.es_unico_por_pais = payload.es_unico_por_pais
    db.commit()
    db.refresh(puesto)
    return puesto


@router.delete("/puestos/{puesto_id}", status_code=204)
def eliminar_puesto(
    puesto_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    puesto = db.get(models.Puesto, puesto_id)
    if not puesto:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    cantidad_personas = db.query(models.Usuario).filter(models.Usuario.puesto_id == puesto_id).count()
    if cantidad_personas > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {cantidad_personas} persona(s) asignada(s) a este puesto",
        )
    db.delete(puesto)
    db.commit()


@router.get("/cab/", response_model=list[schemas.MiembroCABDetalleOut])
def listar_miembros_cab(
    db: Session = Depends(get_db),
    _usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
):
    # Lo consume useEsMiembroCab (cualquier usuario registrado necesita saber
    # si pertenece a algún CAB para que el sidebar decida qué mostrar).
    return db.query(models.MiembroCAB).all()


@router.post("/cab/", response_model=schemas.MiembroCABOut, status_code=201)
def agregar_miembro_cab(
    payload: schemas.MiembroCABCreate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(requerir_admin),
):
    usuario = db.get(models.Usuario, payload.usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    miembro = models.MiembroCAB(**payload.model_dump())
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro
