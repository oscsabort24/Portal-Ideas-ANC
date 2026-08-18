import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from criterios import models, schemas
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


def _validar_departamento_aplica(tipo: TipoCriterio, departamento_id: int | None) -> None:
    """Solo 'entrevista' admite scoping por departamento — clasificacion y
    asignacion_revisor son criterios únicos y globales."""
    if tipo != TipoCriterio.entrevista and departamento_id is not None:
        raise HTTPException(
            status_code=400, detail=f"El tipo '{tipo.value}' no admite scoping por departamento"
        )


# Los endpoints de abajo son admin como todo el resto del módulo: la
# pantalla que los consume (CriteriosView) está detrás de `esAdmin` en el
# sidebar, y estos criterios alimentan a la IA. La clasificación
# automática NO pasa por HTTP (clasificacion/service.py lee CriterioIA
# directo de la BD), así que exigir admin acá no la afecta.
@router.get("/{tipo}", response_model=schemas.CriterioIAOut)
def obtener_criterio_activo(
    tipo: TipoCriterio,
    departamento_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    _validar_departamento_aplica(tipo, departamento_id)
    criterio = (
        db.query(models.CriterioIA).filter_by(tipo=tipo, departamento_id=departamento_id, activo=True).first()
    )
    if not criterio:
        raise HTTPException(status_code=404, detail="No hay un criterio activo todavía")
    return criterio


@router.get("/{tipo}/historial", response_model=list[schemas.CriterioIAOut])
def historial_criterio(
    tipo: TipoCriterio,
    departamento_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    _validar_departamento_aplica(tipo, departamento_id)
    return (
        db.query(models.CriterioIA)
        .filter_by(tipo=tipo, departamento_id=departamento_id)
        .order_by(models.CriterioIA.version.desc())
        .all()
    )


@router.put("/{tipo}", response_model=schemas.CriterioIAOut, status_code=201)
def guardar_criterio(
    tipo: TipoCriterio,
    payload: schemas.GuardarCriterioRequest,
    db: Session = Depends(get_db),
    admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    """Cada guardado crea una versión nueva y desactiva la anterior — no
    existe una edición liviana sin versionar (decisión de negocio: máxima
    trazabilidad/auditoría sobre el texto que la IA efectivamente usa)."""
    _validar_departamento_aplica(tipo, payload.departamento_id)

    pin_admin = db.query(models.PinAdmin).filter_by(usuario_id=admin.id).first()
    if not pin_admin:
        raise HTTPException(status_code=400, detail="Todavía no has definido tu PIN personal")
    if not verificar_pin(payload.pin, pin_admin.pin_hash):
        raise HTTPException(status_code=403, detail="El PIN no es correcto")

    # Bloquea la fila activa (si existe) para serializar guardados
    # concurrentes del mismo (tipo, departamento_id) — evita que dos
    # requests calculen la misma siguiente versión al mismo tiempo.
    anterior = (
        db.query(models.CriterioIA)
        .filter_by(tipo=tipo, departamento_id=payload.departamento_id, activo=True)
        .with_for_update()
        .first()
    )
    siguiente_version = (anterior.version if anterior else 0) + 1
    if anterior:
        anterior.activo = False

    nuevo = models.CriterioIA(
        tipo=tipo,
        departamento_id=payload.departamento_id,
        version=siguiente_version,
        activo=True,
        contenido=payload.contenido,
        descripcion=payload.descripcion,
        creado_por_id=admin.id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/entrevista/cobertura", response_model=list[schemas.CoberturaDepartamentoOut])
def cobertura_entrevista(
    db: Session = Depends(get_db),
    _admin: usuarios_models.Usuario = Depends(requerir_admin),
):
    """Para la UI: qué departamentos tienen una excepción propia de
    entrevista y cuáles usan el texto por defecto."""
    departamentos = (
        db.query(usuarios_models.Departamento).order_by(usuarios_models.Departamento.nombre).all()
    )
    con_excepcion = {
        c.departamento_id
        for c in db.query(models.CriterioIA)
        .filter_by(tipo=TipoCriterio.entrevista, activo=True)
        .filter(models.CriterioIA.departamento_id.isnot(None))
        .all()
    }
    return [
        {"departamento_id": d.id, "nombre": d.nombre, "tiene_excepcion": d.id in con_excepcion}
        for d in departamentos
    ]
