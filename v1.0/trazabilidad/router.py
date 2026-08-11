from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from trazabilidad import schemas, service
from usuarios.dependencies import requerir_admin_o_gerente
from usuarios.models import Departamento, Usuario

router = APIRouter(prefix="/trazabilidad", tags=["trazabilidad"])


@router.get("/flow-control", response_model=list[schemas.FlowControlIdeaOut])
def flow_control(
    db: Session = Depends(get_db),
    _usuario_actual: Usuario = Depends(requerir_admin_o_gerente),
):
    filas = service.construir_flow_control(db)

    nombres_departamento = {d.id: d.nombre for d in db.query(Departamento).all()}
    for fila in filas:
        fila["departamento_nombre"] = nombres_departamento.get(fila["departamento_id"])

    return filas
