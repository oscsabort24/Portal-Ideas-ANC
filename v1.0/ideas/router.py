from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from comites.models import ComiteIdea
from core.claude_client import generar_respuesta, responder_pregunta_idea
from core.database import get_db
from ideas import schemas
from ideas.models import EstadoIdea, Idea, MensajeEntrevista, RolMensaje
from ideas.service import construir_linea_tiempo, siguiente_orden
from revision.models import EstadoRevision, RevisionIdea
from revision.service import crear_revision_para_idea
from riesgo.models import AnalisisRiesgoIdea
from riesgo.service import crear_analisis_riesgo_para_idea
from usuarios.models import MiembroCAB, RolUsuario, Usuario
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/ideas", tags=["ideas"])

SYSTEM_PROMPT_ENTREVISTA = (
    "Eres un entrevistador que ayuda a un colaborador de ANC a documentar una idea. "
    "Sé estricto: si una respuesta es vaga, pide ejemplos concretos antes de aceptarla. "
    "No avances con contenido pobre."
)


@router.post("", response_model=schemas.IdeaOut, status_code=201)
def crear_idea(payload: schemas.IdeaCreate, db: Session = Depends(get_db)):
    autor = db.get(Usuario, payload.autor_id)
    if not autor:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    idea = Idea(titulo=payload.titulo, autor_id=payload.autor_id, estado=EstadoIdea.borrador)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.get("", response_model=list[schemas.IdeaOut])
def listar_ideas(
    autor_id: int | None = None,
    estado: EstadoIdea | None = None,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    # Solo un admin puede ver ideas de otros usuarios (ej. Panel de
    # administración, que no manda autor_id para traer todas). Cualquier
    # no-admin queda forzado a su propio autor_id sin importar qué haya
    # mandado — así nadie puede ver ideas ajenas ni llamando la API
    # directamente sin pasar por el frontend.
    if usuario_actual.rol != RolUsuario.admin:
        autor_id = usuario_actual.id

    query = db.query(Idea)
    if autor_id is not None:
        query = query.filter(Idea.autor_id == autor_id)
    if estado is not None:
        query = query.filter(Idea.estado == estado)
    return query.order_by(Idea.fecha_creacion.desc()).all()


@router.get("/{idea_id}", response_model=schemas.IdeaDetalleOut)
def obtener_idea(idea_id: int, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    return idea


@router.get("/{idea_id}/linea-tiempo", response_model=list[schemas.EventoLineaTiempoOut])
def linea_tiempo(idea_id: int, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    return construir_linea_tiempo(db, idea)


@router.post("/{idea_id}/mensajes", response_model=schemas.RespuestaEntrevistaOut, status_code=201)
def enviar_mensaje(
    idea_id: int, payload: schemas.MensajeEntrevistaCreate, db: Session = Depends(get_db)
):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    if idea.estado == EstadoIdea.enviada:
        revision = db.query(RevisionIdea).filter_by(idea_id=idea_id).first()
        if not revision or revision.estado != EstadoRevision.cambios_solicitados:
            raise HTTPException(status_code=400, detail="La idea ya fue enviada, no admite más mensajes")

    # Solo sobrescribe si el autor mandó algo esta vez — si el campo viene
    # vacío en un mensaje posterior, no debe borrar un valor ya guardado.
    if payload.sugerencia_revisor_autor is not None:
        idea.sugerencia_revisor_autor = payload.sugerencia_revisor_autor
    if payload.motivo_sugerencia_revisor_autor is not None:
        idea.motivo_sugerencia_revisor_autor = payload.motivo_sugerencia_revisor_autor

    orden_usuario = siguiente_orden(db, idea_id)
    mensaje_usuario = MensajeEntrevista(
        idea_id=idea_id, rol=RolMensaje.usuario, contenido=payload.contenido, orden=orden_usuario
    )
    db.add(mensaje_usuario)
    db.flush()

    historial = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    mensajes_para_ia = [{"role": m.rol.value, "content": m.contenido} for m in historial]

    respuesta = generar_respuesta(mensajes_para_ia, SYSTEM_PROMPT_ENTREVISTA)

    mensaje_asistente = MensajeEntrevista(
        idea_id=idea_id,
        rol=RolMensaje.asistente,
        contenido=respuesta["message"],
        orden=orden_usuario + 1,
    )
    db.add(mensaje_asistente)

    if respuesta["entrevista_completa"]:
        if idea.estado == EstadoIdea.borrador:
            # Primera vez que se completa la entrevista — no existe RevisionIdea todavía.
            idea.estado = EstadoIdea.enviada
            idea.fecha_envio = datetime.now(timezone.utc)
            crear_revision_para_idea(db, idea)
            crear_analisis_riesgo_para_idea(db, idea, mensajes_para_ia)
        else:
            # idea.estado ya era "enviada": solo se llega aquí porque el guard de arriba
            # confirmó que existe una RevisionIdea en cambios_solicitados — es una
            # rectificación. Reactiva la revisión existente, nunca crea una nueva
            # (RevisionIdea.idea_id es unique).
            revision = db.query(RevisionIdea).filter_by(idea_id=idea_id).first()
            revision.estado = EstadoRevision.pendiente_revision
            revision.fecha_asignacion = datetime.now(timezone.utc)

    db.commit()
    db.refresh(idea)
    db.refresh(mensaje_usuario)
    db.refresh(mensaje_asistente)

    return schemas.RespuestaEntrevistaOut(
        idea=idea, mensaje_usuario=mensaje_usuario, mensaje_asistente=mensaje_asistente
    )


def _tiene_acceso_revision_o_comite(db: Session, idea: Idea, usuario: Usuario) -> bool:
    """Acceso al resumen/preguntas de una idea: admin, el revisor asignado
    (RevisionIdea.revisor_id), o un miembro del CAB del tipo correspondiente
    si la idea ya llegó a comité — mismo patrón que
    documentos/router.py:_validar_acceso."""
    if usuario.rol == RolUsuario.admin:
        return True

    revision = db.query(RevisionIdea).filter_by(idea_id=idea.id).first()
    if revision and revision.revisor_id == usuario.id:
        return True

    comite = db.query(ComiteIdea).filter_by(idea_id=idea.id).first()
    if comite:
        es_miembro = (
            db.query(MiembroCAB)
            .filter(MiembroCAB.usuario_id == usuario.id, MiembroCAB.tipo_cab == comite.tipo_cab)
            .first()
            is not None
        )
        if es_miembro:
            return True

    return False


@router.get("/{idea_id}/resumen", response_model=schemas.ResumenIdeaOut)
def obtener_resumen(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    if not _tiene_acceso_revision_o_comite(db, idea, usuario_actual):
        raise HTTPException(status_code=403, detail="No tienes acceso al resumen de esta idea")

    ultimo_mensaje_asistente = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id, MensajeEntrevista.rol == RolMensaje.asistente)
        .order_by(MensajeEntrevista.orden.desc())
        .first()
    )
    if not ultimo_mensaje_asistente:
        raise HTTPException(status_code=404, detail="Esta idea todavía no tiene un resumen disponible")

    analisis_riesgo = db.query(AnalisisRiesgoIdea).filter_by(idea_id=idea_id).first()

    return schemas.ResumenIdeaOut(
        resumen=ultimo_mensaje_asistente.contenido,
        categoria_riesgo=analisis_riesgo.categoria.value if analisis_riesgo else None,
    )


@router.post("/{idea_id}/preguntar", response_model=schemas.RespuestaPreguntaOut)
def preguntar(
    idea_id: int,
    payload: schemas.PreguntarRequest,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    if not _tiene_acceso_revision_o_comite(db, idea, usuario_actual):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta idea")

    historial = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    mensajes_para_ia = [{"role": m.rol.value, "content": m.contenido} for m in historial]

    respuesta = responder_pregunta_idea(mensajes_para_ia, payload.pregunta)
    return schemas.RespuestaPreguntaOut(respuesta=respuesta)
