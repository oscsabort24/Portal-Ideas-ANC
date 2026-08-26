from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from comites.models import ComiteIdea
from comites.service import departamentos_visibles, idea_departamento_visible
from core.claude_client import EstadoBloque, generar_respuesta, generar_resumen_idea, responder_pregunta_idea
from core.database import get_db
from ideas import schemas
from ideas.models import EstadoIdea, Idea, MensajeEntrevista, OrigenPregunta, PreguntaIdea, RolMensaje
from ideas.service import construir_linea_tiempo, historial_para_ia, siguiente_orden
from revision.models import EstadoRevision, RevisionIdea
from revision.service import crear_revision_para_idea
from riesgo.models import AnalisisRiesgoIdea
from riesgo.service import crear_analisis_riesgo_para_idea
from permisos.models import ClavePermiso
from permisos.service import tiene_permiso
from usuarios.models import RolUsuario, Usuario
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/ideas", tags=["ideas"])

# Tono deliberadamente ACOGEDOR, no exigente. La versión anterior decía
# "Sé estricto (...) No avances con contenido pobre", lo que hacía que la IA
# bloqueara la conversación ante un "no sé" — el colaborador operativo que
# usa esto no maneja presupuestos ni plazos y quedaba en bucle. La calidad
# del dato se recupera después, en la revisión; el abandono del formulario
# no se recupera nunca.
SYSTEM_PROMPT_ENTREVISTA = (
    "Sos un compañero de trabajo de ANC que ayuda a una persona a contar su idea "
    "para mejorar algo en su trabajo. No sos un formulario ni un auditor: sos "
    "alguien curioso que escucha y pregunta.\n\n"
    "Quien te habla puede ser cualquier persona de la empresa — un chofer, alguien "
    "de bodega, de servicio al cliente. Probablemente nunca gestionó un proyecto y "
    "no tiene por qué saber de presupuestos, plazos ni metodologías. Hablale como "
    "le hablarías a un compañero en el pasillo: en voseo, con frases cortas, sin "
    "ninguna palabra técnica.\n\n"
    "Si algo no lo sabe, está perfecto — anotalo y seguí adelante. Nunca la hagas "
    "sentir que su respuesta no sirve."
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


# Quién ve el Panel de administración (todas las ideas del sistema, de
# solo lectura) — determinado por el permiso configurable
# ve_todas_las_ideas (ver permisos/, admin sigue siendo bypass
# hardcodeado). El resto de pantallas admin-only (Usuarios, Criterios IA,
# Notificaciones) siguen exclusivas de admin vía requerir_admin en sus
# propios routers, sin relación con esto.


@router.get("", response_model=list[schemas.IdeaOut])
def listar_ideas(
    autor_id: int | None = None,
    estado: EstadoIdea | None = None,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    # Quien no tiene el permiso ve_todas_las_ideas queda forzado a su
    # propio autor_id sin importar qué haya mandado — así nadie puede ver
    # ideas ajenas ni llamando la API directamente sin pasar por el frontend.
    if not tiene_permiso(db, usuario_actual, ClavePermiso.ve_todas_las_ideas):
        autor_id = usuario_actual.id

    query = db.query(Idea)
    if autor_id is not None:
        query = query.filter(Idea.autor_id == autor_id)
    if estado is not None:
        query = query.filter(Idea.estado == estado)
    ideas = query.order_by(Idea.fecha_creacion.desc()).all()

    # Import local: trazabilidad/ ya importa de ideas/, así que a nivel de
    # módulo esto sería un ciclo.
    from trazabilidad.service import estados_flow_por_idea

    # En bloque para las ideas ya filtradas — 5 queries fijas, no 5 por idea.
    estados_flow = estados_flow_por_idea(db, ideas)
    return [
        schemas.IdeaOut.model_validate(idea).model_copy(
            update={"estado_flow": estados_flow.get(idea.id)}
        )
        for idea in ideas
    ]


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
    if tiene_permiso(db, usuario, ClavePermiso.ve_todas_las_ideas):
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
    idea = _obtener_idea_visible(db, idea_id, usuario_actual)

    # Mismo import local y misma función en bloque que listar_ideas — acá con
    # una sola idea. El detalle lo necesita para el stepper de progreso; antes
    # estado_flow solo lo llenaba el listado y en el detalle venía en null.
    from trazabilidad.service import estados_flow_por_idea

    estados_flow = estados_flow_por_idea(db, [idea])
    return schemas.IdeaDetalleOut.model_validate(idea).model_copy(
        update={"estado_flow": estados_flow.get(idea.id)}
    )


@router.get("/{idea_id}/linea-tiempo", response_model=list[schemas.EventoLineaTiempoOut])
def linea_tiempo(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea_visible(db, idea_id, usuario_actual)
    return construir_linea_tiempo(db, idea)


def _validar_autor_o_admin(idea: Idea, usuario: Usuario) -> None:
    """Solo el autor de la idea o un admin pueden escribir en ella (mandar
    mensajes de entrevista, enviarla). Mismo criterio de excepción de admin
    que _puede_ver_idea (más arriba), pero sin el acceso de revisor/CAB:
    escribir en la entrevista de otra persona no es un caso legítimo ni
    para quien la revisa, solo para su autor o un admin.
    """
    if usuario.rol == RolUsuario.admin:
        return
    if idea.autor_id == usuario.id:
        return
    raise HTTPException(status_code=403, detail="No tienes acceso a esta idea")


@router.post("/{idea_id}/mensajes", response_model=schemas.RespuestaEntrevistaOut, status_code=201)
def enviar_mensaje(
    idea_id: int,
    payload: schemas.MensajeEntrevistaCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    _validar_autor_o_admin(idea, usuario_actual)

    # Reintento del MISMO intento de envío: el frontend conserva la clave
    # mientras el envío no haya tenido éxito (ver ChatEntrevista.tsx), así
    # que si el turno anterior sí se guardó pero el cliente no llegó a ver
    # la respuesta (timeout de 40s, red caída), acá se devuelve el turno ya
    # generado en vez de crear uno nuevo y volver a llamar a la IA.
    # NO usar historial_para_ia acá: esta búsqueda tiene que ver los mensajes
    # tal como están guardados, degradados incluidos. Si se filtraran, un
    # reintento no encontraría el turno ya persistido, crearía uno nuevo con
    # la misma clave y violaría el índice único de idempotency_key.
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
                # Sin `opciones`: son efímeras y no se persisten (ver
                # schemas.RespuestaEntrevistaOut), así que un reintento del
                # mismo turno devuelve el texto pero no los botones. Es el
                # mismo trato que una recarga de página.
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

    mensajes_para_ia = historial_para_ia(db, idea_id)

    respuesta = generar_respuesta(mensajes_para_ia, SYSTEM_PROMPT_ENTREVISTA, idea.autor.departamento_id)

    mensaje_asistente = MensajeEntrevista(
        idea_id=idea_id,
        rol=RolMensaje.asistente,
        contenido=respuesta["message"],
        orden=orden_usuario + 1,
        # generar_respuesta marca en el origen si este turno es texto de
        # respaldo del backend en vez de contenido real de la IA. Se guarda
        # para poder excluirlo del contexto en turnos siguientes.
        degradado=respuesta["degradado"],
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
        idea=idea,
        mensaje_usuario=mensaje_usuario,
        mensaje_asistente=mensaje_asistente,
        opciones=respuesta["options"],
    )


@router.post("/{idea_id}/enviar", response_model=schemas.IdeaOut)
def enviar_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
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
    _validar_autor_o_admin(idea, usuario_actual)

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

        crear_analisis_riesgo_para_idea(db, idea, historial_para_ia(db, idea_id))
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
    (RevisionIdea.revisor_id), o un miembro del CAB con acceso al
    departamento del autor si la idea ya llegó a comité — mismo patrón
    que documentos/router.py:_validar_acceso (departamentos_visibles +
    idea_departamento_visible, no tipo_cab — migrado de la implementación
    vieja que quedó desalineada tras el cambio a CAB por departamento).

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
        departamentos = departamentos_visibles(db, usuario)
        if idea_departamento_visible(idea.autor.departamento_id, departamentos):
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

    # Este endpoint necesita el historial en DOS versiones, y la diferencia
    # importa:
    #
    # - Filtrado (historial_para_ia) para lo que alimenta a la IA y para el
    #   texto de respaldo: sin el filtro, el "resumen" que ve un revisor podía
    #   terminar siendo literalmente "Hubo un problema técnico al procesar tu
    #   respuesta", porque ese era el último turno del asistente.
    # - SIN filtrar para invalidar el cache: cualquier mensaje nuevo invalida
    #   el resumen cacheado, incluso uno degradado — marca que la
    #   conversación se movió desde que se generó.
    mensajes_para_ia = historial_para_ia(db, idea_id)

    ultimo_mensaje = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden.desc())
        .first()
    )
    ultimo_texto_asistente = next(
        (m["content"] for m in reversed(mensajes_para_ia) if m["role"] == RolMensaje.asistente.value),
        None,
    )
    if ultimo_mensaje is None or ultimo_texto_asistente is None:
        raise HTTPException(status_code=404, detail="Esta idea todavía no tiene un resumen disponible")

    analisis_riesgo = db.query(AnalisisRiesgoIdea).filter_by(idea_id=idea_id).first()

    # Cache en Idea.resumen_ia: válido mientras no haya mensajes nuevos desde
    # que se generó (comparar contra el timestamp del último mensaje del
    # transcript, sin importar el rol — una respuesta nueva del colaborador
    # también invalida el resumen, no solo un turno del asistente).
    cache_vigente = (
        idea.resumen_ia is not None
        and idea.resumen_ia_generado_en is not None
        and idea.resumen_ia_generado_en >= ultimo_mensaje.creado_en
    )

    if cache_vigente:
        resumen_texto = idea.resumen_ia
    else:
        resumen_generado = generar_resumen_idea(mensajes_para_ia)
        if resumen_generado is not None:
            idea.resumen_ia = resumen_generado
            idea.resumen_ia_generado_en = datetime.now(timezone.utc)
            db.commit()
            resumen_texto = resumen_generado
        else:
            # Fallback si la IA falla (ver generar_resumen_idea): NO es un
            # resumen sintetizado, es el último turno del asistente — mejor
            # que un mensaje de error crudo, mismo criterio que ya se usaba
            # acá antes de tener resumen real.
            resumen_texto = "Último intercambio de la entrevista:\n" + ultimo_texto_asistente

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

    respuesta = responder_pregunta_idea(historial_para_ia(db, idea_id), payload.pregunta)

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
