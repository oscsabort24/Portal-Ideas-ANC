from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.claude_client import generar_respuesta
from core.database import get_db
from ideas import schemas
from ideas.models import EstadoIdea, Idea, MensajeEntrevista, RolMensaje
from ideas.service import siguiente_orden
from revision.models import EstadoRevision, RevisionIdea
from revision.service import crear_revision_para_idea
from usuarios.models import Usuario

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
):
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
