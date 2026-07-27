from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from comites.models import ComiteIdea
from core.claude_client import EstadoBloque, generar_respuesta, responder_pregunta_idea
from core.database import get_db
from ideas import schemas
from ideas.models import EstadoIdea, Idea, MensajeEntrevista, OrigenPregunta, PreguntaIdea, RolMensaje
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
def crear_idea(
    payload: schemas.IdeaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    """Cualquier usuario registrado puede crear una idea — es la acción
    principal de un colaborador, no requiere rol especial.

    El autor SIEMPRE es quien hace la request. `autor_id` ya no se acepta
    del payload: mientras se aceptaba, cualquier usuario autenticado podía
    crear una idea a nombre de otra persona con solo cambiar un número, y
    esa idea después arrastraba al autor falso por todo el flujo (la
    revisión se asigna según el departamento del autor, los documentos se
    generan a su nombre). No existe ningún caso legítimo de crear una idea
    para un tercero — el único llamador es FormularioNuevaIdea.tsx, que ya
    mandaba el id del usuario en sesión.
    """
    idea = Idea(titulo=payload.titulo, autor_id=usuario_actual.id, estado=EstadoIdea.borrador)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


# admin y gerente ven el Panel de administración (todas las ideas del
# sistema, de solo lectura) — el resto de pantallas admin-only (Usuarios,
# Clasificación, Criterios IA, Notificaciones) siguen exclusivas de admin
# vía requerir_admin en sus propios routers, sin relación con esto.
ROLES_VEN_TODAS_LAS_IDEAS = (RolUsuario.admin, RolUsuario.gerente)


@router.get("", response_model=list[schemas.IdeaOut])
def listar_ideas(
    autor_id: int | None = None,
    estado: EstadoIdea | None = None,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    # Solo admin/gerente pueden ver ideas de otros usuarios (ej. Panel de
    # administración, que no manda autor_id para traer todas). Cualquier
    # otro rol queda forzado a su propio autor_id sin importar qué haya
    # mandado — así nadie puede ver ideas ajenas ni llamando la API
    # directamente sin pasar por el frontend.
    if usuario_actual.rol not in ROLES_VEN_TODAS_LAS_IDEAS:
        autor_id = usuario_actual.id

    query = db.query(Idea)
    if autor_id is not None:
        query = query.filter(Idea.autor_id == autor_id)
    if estado is not None:
        query = query.filter(Idea.estado == estado)
    return query.order_by(Idea.fecha_creacion.desc()).all()


def _puede_ver_idea(db: Session, idea: Idea, usuario: Usuario) -> bool:
    """Quién puede leer una idea concreta y su línea de tiempo.

    Estar autenticado no alcanza: sin esto, cualquier colaborador podía leer
    la entrevista completa de la idea de cualquier otro con solo cambiar el
    id en la URL. GET /ideas (el listado) ya filtraba por autor desde antes
    — esto cierra la lectura individual, que era la vía de escape.

    Se permite a:
      - admin y gerente, que ya ven TODAS las ideas en el listado y navegan
        al detalle desde el Panel de administración (PanelAdmin.tsx). Excluir
        a gerente rompería ese panel, así que se reutiliza el mismo criterio
        que GET /ideas en vez de inventar uno distinto.
      - el AUTOR de la idea.
      - el revisor asignado y los miembros del CAB del tipo correspondiente,
        vía _tiene_acceso_revision_o_comite (definida más abajo), que ya
        implementa esa parte para el resumen y el mini-chat.

    OJO con la diferencia: _tiene_acceso_revision_o_comite excluye al autor
    a propósito (ver su docstring — el resumen es una herramienta de quien
    revisa, no del autor). Acá el autor SÍ entra: es su propia idea.
    """
    if usuario.rol in ROLES_VEN_TODAS_LAS_IDEAS:
        return True
    if idea.autor_id == usuario.id:
        return True
    return _tiene_acceso_revision_o_comite(db, idea, usuario)


def _obtener_idea_visible(db: Session, idea_id: int, usuario: Usuario) -> Idea:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    if not _puede_ver_idea(db, idea, usuario):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta idea")
    return idea


@router.get("/{idea_id}", response_model=schemas.IdeaDetalleOut)
def obtener_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    return _obtener_idea_visible(db, idea_id, usuario_actual)


@router.get("/{idea_id}/linea-tiempo", response_model=list[schemas.EventoLineaTiempoOut])
def linea_tiempo(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea_visible(db, idea_id, usuario_actual)
    return construir_linea_tiempo(db, idea)


@router.post("/{idea_id}/mensajes", response_model=schemas.RespuestaEntrevistaOut, status_code=201)
def enviar_mensaje(
    idea_id: int,
    payload: schemas.MensajeEntrevistaCreate,
    db: Session = Depends(get_db),
    _usuario_actual: Usuario = Depends(obtener_usuario_actual),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")

    # Reintento del MISMO intento de envío: el frontend conserva la clave
    # mientras el envío no haya tenido éxito (ver ChatEntrevista.tsx), así
    # que si el turno anterior sí se guardó pero el cliente no llegó a ver
    # la respuesta (timeout de 40s, red caída), acá se devuelve el turno ya
    # generado en vez de crear uno nuevo y volver a llamar a la IA.
    if idempotency_key:
        previo = (
            db.query(MensajeEntrevista)
            .filter(
                MensajeEntrevista.idea_id == idea_id,
                MensajeEntrevista.idempotency_key == idempotency_key,
            )
            .first()
        )
        if previo is not None:
            respuesta_previa = (
                db.query(MensajeEntrevista)
                .filter(
                    MensajeEntrevista.idea_id == idea_id,
                    MensajeEntrevista.orden == previo.orden + 1,
                )
                .first()
            )
            if respuesta_previa is not None:
                return schemas.RespuestaEntrevistaOut(
                    idea=idea, mensaje_usuario=previo, mensaje_asistente=respuesta_previa
                )
            # Caso patológico: quedó el mensaje del usuario sin la respuesta
            # del asistente (el proceso murió entre un add y el otro). No se
            # puede devolver un turno completo ni reusar la clave sin violar
            # el índice único, así que se pide reintentar con clave nueva.
            raise HTTPException(
                status_code=409,
                detail="El envío anterior quedó incompleto. Volvé a intentarlo.",
            )

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
        idea_id=idea_id,
        rol=RolMensaje.usuario,
        contenido=payload.contenido,
        orden=orden_usuario,
        idempotency_key=idempotency_key,
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

    # None solo ocurre en una respuesta degradada (fallo de API o de
    # parseo) — se mantiene el último progreso_bloques conocido en vez de
    # borrarlo, igual que sugerencia_revisor_autor arriba.
    if respuesta["progreso_bloques"] is not None:
        idea.progreso_bloques = respuesta["progreso_bloques"]

    # El envío YA NO lo dispara la IA (ver REGLA DE CIERRE en
    # core/claude_client.py:_CRITERIOS_ENTREVISTA) — entrevista_completa
    # siempre viene en False. Quien decide enviar es la persona, vía botón
    # "Enviar idea" -> POST /ideas/{idea_id}/enviar (ver más abajo).

    db.commit()
    db.refresh(idea)
    db.refresh(mensaje_usuario)
    db.refresh(mensaje_asistente)

    return schemas.RespuestaEntrevistaOut(
        idea=idea, mensaje_usuario=mensaje_usuario, mensaje_asistente=mensaje_asistente
    )


@router.post("/{idea_id}/enviar", response_model=schemas.IdeaOut)
def enviar_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    _usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    """Envío manual de la idea, disparado por el botón "Enviar idea" del
    chat (ver ChatEntrevista.tsx) — reemplaza el cierre automático que
    antes decidía la IA vía entrevista_completa (ver
    core/claude_client.py:_CRITERIOS_ENTREVISTA, REGLA DE CIERRE).

    Hace exactamente lo que antes hacía el bloque `if
    respuesta["entrevista_completa"]` dentro de enviar_mensaje: primer
    envío (borrador -> enviada, crea revisión + análisis de riesgo) o
    reenvío tras cambios_solicitados (reactiva la revisión existente).
    progreso_bloques se revalida en el servidor — no se confía en que el
    frontend solo muestre el botón cuando corresponde.
    """
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")

    progreso = idea.progreso_bloques
    bloques_completos = bool(progreso) and all(
        estado == EstadoBloque.completado.value for estado in progreso.values()
    )
    if not bloques_completos:
        raise HTTPException(
            status_code=400, detail="Todavía faltan bloques de la entrevista por completar"
        )

    if idea.estado == EstadoIdea.borrador:
        idea.estado = EstadoIdea.enviada
        idea.fecha_envio = datetime.now(timezone.utc)
        crear_revision_para_idea(db, idea)

        historial = (
            db.query(MensajeEntrevista)
            .filter(MensajeEntrevista.idea_id == idea_id)
            .order_by(MensajeEntrevista.orden)
            .all()
        )
        mensajes_para_ia = [{"role": m.rol.value, "content": m.contenido} for m in historial]
        crear_analisis_riesgo_para_idea(db, idea, mensajes_para_ia)
    else:
        revision = db.query(RevisionIdea).filter_by(idea_id=idea_id).first()
        if not revision or revision.estado != EstadoRevision.cambios_solicitados:
            raise HTTPException(
                status_code=400, detail="Esta idea ya fue enviada, no admite un nuevo envío"
            )
        # Rectificación tras "cambios_solicitados": reactiva la revisión
        # existente, nunca crea una nueva (RevisionIdea.idea_id es unique).
        revision.estado = EstadoRevision.pendiente_revision
        revision.fecha_asignacion = datetime.now(timezone.utc)

    db.commit()
    db.refresh(idea)
    return idea


def _tiene_acceso_revision_o_comite(db: Session, idea: Idea, usuario: Usuario) -> bool:
    """Acceso al resumen/preguntas de una idea: admin, el revisor asignado
    (RevisionIdea.revisor_id), o un miembro del CAB del tipo correspondiente
    si la idea ya llegó a comité — mismo patrón que
    documentos/router.py:_validar_acceso.

    A diferencia de ese patrón, aquí el AUTOR de la idea no tiene acceso —
    decisión intencional confirmada: el resumen/mini-chat es una herramienta
    para que quien revisa o decide entienda mejor la idea antes de resolver,
    no una vista del autor sobre su propia idea (que ya ve la entrevista
    completa de todas formas). No es un descuido.
    """
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

    resumen_texto = ultimo_mensaje_asistente.contenido

    # Una idea con fila en ComiteIdea ya pasó por revisión aprobada —
    # revision/router.py:mis_revisiones solo lista revisiones en estado
    # pendiente_revision, así que en ese punto la idea YA NO aparece en
    # "Mis revisiones". Es decir, mientras existe ComiteIdea, el único
    # lugar desde donde se puede estar pidiendo este resumen es CAB (o el
    # panel de solo-lectura de admin) — nunca la pantalla de Revisión.
    # Por eso alcanza con checar existencia de ComiteIdea, sin necesitar
    # que el frontend mande un parámetro de "contexto" explícito.
    comite = db.query(ComiteIdea).filter_by(idea_id=idea_id).first()
    if comite:
        preguntas_revision = (
            db.query(PreguntaIdea)
            .filter(PreguntaIdea.idea_id == idea_id, PreguntaIdea.origen == OrigenPregunta.revision)
            .order_by(PreguntaIdea.creada_en)
            .all()
        )
        if preguntas_revision:
            bloque = "\n\n--- Preguntas indagadas durante la revisión ---\n" + "\n".join(
                f"P: {p.pregunta}\nR: {p.respuesta}" for p in preguntas_revision
            )
            resumen_texto += bloque

    return schemas.ResumenIdeaOut(
        resumen=resumen_texto,
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

    db.add(
        PreguntaIdea(
            idea_id=idea_id,
            origen=payload.origen,
            pregunta=payload.pregunta,
            respuesta=respuesta,
            preguntada_por_id=usuario_actual.id,
        )
    )
    db.commit()

    return schemas.RespuestaPreguntaOut(respuesta=respuesta)
