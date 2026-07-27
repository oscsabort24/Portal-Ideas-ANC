import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from criterios import models, schemas
from criterios.archivos import borrar_archivo, extraer_texto_docx, guardar_archivo, validar_extension
from criterios.models import TipoCriterio
from criterios.seguridad import hashear_pin, verificar_pin
from usuarios import models as usuarios_models
from usuarios.dependencies import requerir_admin

router = APIRouter(prefix="/criterios", tags=["criterios"])

MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15
MAX_CAMBIOS_POR_DIA = 3


def _minutos_restantes(bloqueado_hasta: datetime) -> int:
    ahora = datetime.now(timezone.utc)
    return max(1, math.ceil((bloqueado_hasta - ahora).total_seconds() / 60))


@router.post("/pin", status_code=204)
def definir_pin(
    payload: schemas.PinDefinir,
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    pin_existente = db.query(models.PinAdmin).filter_by(usuario_id=admin.id).first()
    ahora = datetime.now(timezone.utc)

    if not pin_existente:
        # Primera vez: no cuenta para el límite diario ni pasa por ningún chequeo.
        db.add(models.PinAdmin(usuario_id=admin.id, pin_hash=hashear_pin(payload.pin_nuevo)))
        db.commit()
        return

    # 1. ¿Bloqueado por intentos fallidos?
    if pin_existente.bloqueado_hasta and pin_existente.bloqueado_hasta > ahora:
        raise HTTPException(
            status_code=403,
            detail=f"Demasiados intentos fallidos. Intenta de nuevo en {_minutos_restantes(pin_existente.bloqueado_hasta)} minutos.",
        )

    # 2. ¿Límite diario de cambios exitosos alcanzado? (se revisa antes de gastar un intento)
    hoy = ahora.date()
    cambios_hoy_efectivo = pin_existente.cambios_hoy if pin_existente.fecha_ultimo_cambio == hoy else 0
    if cambios_hoy_efectivo >= MAX_CAMBIOS_POR_DIA:
        raise HTTPException(
            status_code=403,
            detail=f"Ya alcanzaste el límite de {MAX_CAMBIOS_POR_DIA} cambios de PIN hoy. Intenta de nuevo mañana.",
        )

    # 3. Verifica el PIN actual.
    if not payload.pin_actual or not verificar_pin(payload.pin_actual, pin_existente.pin_hash):
        pin_existente.intentos_fallidos += 1
        if pin_existente.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
            pin_existente.bloqueado_hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=f"Demasiados intentos fallidos. Intenta de nuevo en {MINUTOS_BLOQUEO} minutos.",
            )
        db.commit()
        intentos_restantes = MAX_INTENTOS_FALLIDOS - pin_existente.intentos_fallidos
        raise HTTPException(
            status_code=403,
            detail=(
                "El PIN actual no es correcto. "
                f"Te quedan {intentos_restantes} intento(s) antes de bloquear temporalmente los cambios de PIN."
            ),
        )

    # PIN correcto: resetea el bloqueo, actualiza el hash y el contador diario.
    pin_existente.intentos_fallidos = 0
    pin_existente.bloqueado_hasta = None
    pin_existente.pin_hash = hashear_pin(payload.pin_nuevo)
    pin_existente.cambios_hoy = cambios_hoy_efectivo + 1
    pin_existente.fecha_ultimo_cambio = hoy
    db.commit()


@router.get("/pin/estado")
def estado_pin(
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    tiene_pin = db.query(models.PinAdmin).filter_by(usuario_id=admin.id).first() is not None
    return {"tiene_pin": tiene_pin}


def _obtener_documento_activo(db: Session, tipo: TipoCriterio) -> models.DocumentoCriterio:
    documento = db.query(models.DocumentoCriterio).filter_by(tipo=tipo, activo=True).first()
    if not documento:
        raise HTTPException(status_code=404, detail=f"No hay un documento activo de tipo '{tipo.value}' todavía")
    return documento


@router.get("/{tipo}", response_model=schemas.DocumentoCriterioOut)
def obtener_documento_activo(tipo: TipoCriterio, db: Session = Depends(get_db)):
    return _obtener_documento_activo(db, tipo)


@router.get("/{tipo}/descargar")
def descargar_documento_activo(tipo: TipoCriterio, db: Session = Depends(get_db)):
    documento = _obtener_documento_activo(db, tipo)
    return FileResponse(documento.ruta_archivo, filename=documento.nombre_archivo)


@router.get("/{tipo}/historial", response_model=list[schemas.DocumentoCriterioOut])
def historial_documento(tipo: TipoCriterio, db: Session = Depends(get_db)):
    return (
        db.query(models.DocumentoCriterio)
        .filter_by(tipo=tipo)
        .order_by(models.DocumentoCriterio.version.desc())
        .all()
    )


def _max_version(db: Session, tipo: TipoCriterio) -> int:
    maximo = (
        db.query(models.DocumentoCriterio.version)
        .filter_by(tipo=tipo)
        .order_by(models.DocumentoCriterio.version.desc())
        .first()
    )
    return maximo[0] if maximo else 0


@router.post("/{tipo}", response_model=schemas.DocumentoCriterioOut, status_code=201)
def subir_documento(
    tipo: TipoCriterio,
    pin: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    extension = validar_extension(archivo)

    pin_admin = db.query(models.PinAdmin).filter_by(usuario_id=admin.id).first()
    if not pin_admin:
        raise HTTPException(status_code=400, detail="Todavía no has definido tu PIN personal")
    if not verificar_pin(pin, pin_admin.pin_hash):
        raise HTTPException(status_code=403, detail="El PIN no es correcto")

    # Bloquea la fila activa de este tipo (si existe) para serializar subidas
    # concurrentes del mismo tipo — evita que dos requests calculen la misma
    # siguiente versión al mismo tiempo.
    anterior = (
        db.query(models.DocumentoCriterio)
        .filter_by(tipo=tipo, activo=True)
        .with_for_update()
        .first()
    )
    siguiente_version = (anterior.version if anterior else _max_version(db, tipo)) + 1

    ruta_archivo = guardar_archivo(archivo, tipo.value, siguiente_version, extension)

    # Precarga `contenido` para que ya sea editable sin tener que volver a
    # subir el archivo — solo para .docx, no hay extracción de .pdf (ver
    # migración 0c05a39f74d4 para el porqué).
    contenido_extraido: str | None = None
    if extension == ".docx":
        try:
            contenido_extraido = extraer_texto_docx(ruta_archivo)
        except Exception:
            contenido_extraido = None

    try:
        if anterior:
            anterior.activo = False
        nuevo = models.DocumentoCriterio(
            tipo=tipo,
            nombre_archivo=archivo.filename,
            ruta_archivo=ruta_archivo,
            version=siguiente_version,
            activo=True,
            contenido=contenido_extraido,
            subido_por_id=admin.id,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
    except IntegrityError:
        db.rollback()
        borrar_archivo(ruta_archivo)
        raise HTTPException(
            status_code=409,
            detail="Otra persona subió una versión de este documento al mismo tiempo. Intenta de nuevo.",
        )

    return nuevo


@router.patch("/{documento_id}", response_model=schemas.DocumentoCriterioOut)
def editar_documento(
    documento_id: int,
    payload: schemas.DocumentoCriterioEditar,
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    """Edita `contenido`/`descripcion` de la versión ACTIVA in-place — no
    crea una versión nueva (a diferencia de POST /criterios/{tipo}, que sí
    reemplaza el documento y sube de versión). Ver criterios/models.py
    para el razonamiento de por qué una edición de texto no versiona."""
    documento = db.get(models.DocumentoCriterio, documento_id)
    if not documento or not documento.activo:
        raise HTTPException(status_code=404, detail="No hay un documento activo con ese id")

    pin_admin = db.query(models.PinAdmin).filter_by(usuario_id=admin.id).first()
    if not pin_admin:
        raise HTTPException(status_code=400, detail="Todavía no has definido tu PIN personal")
    if not verificar_pin(payload.pin, pin_admin.pin_hash):
        raise HTTPException(status_code=403, detail="El PIN no es correcto")

    if payload.contenido is not None:
        documento.contenido = payload.contenido
    if payload.descripcion is not None:
        documento.descripcion = payload.descripcion
    documento.actualizado_por_id = admin.id
    documento.actualizado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(documento)
    return documento

    return nuevo
