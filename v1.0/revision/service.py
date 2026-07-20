"""Lógica de asignación de revisión, llamada desde ideas/router.py cuando una idea se envía.

*** ASIGNACIÓN AUTOMÁTICA POR IA, CON FALLBACK ***
Se intenta primero que la IA sugiera, a partir del CONTENIDO real de la
idea (no solo el departamento del autor), a qué departamento le
corresponde revisarla — considerando también, si existe, una sugerencia
opcional del autor (ver asignar_revisor_ia en core/claude_client.py).

Si la IA falla por cualquier motivo, o si el departamento que sugiere no
tiene ningún encargado_area activo, se cae al comportamiento original:
mismo departamento del autor. Si tampoco hay nadie ahí, la idea queda
"pendiente_asignacion" para que un admin la asigne manualmente. Esto
NUNCA debe romper el envío de la idea.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.claude_client import asignar_revisor_ia
from ideas.models import Idea, MensajeEntrevista
from revision.models import EstadoRevision, RevisionIdea
from usuarios.models import Departamento, RolUsuario, Usuario

logger = logging.getLogger(__name__)


def _historial_para_ia(db: Session, idea_id: int) -> list[dict]:
    mensajes = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    return [{"role": m.rol.value, "content": m.contenido} for m in mensajes]


def _buscar_encargado_activo(db: Session, departamento_id: int) -> Usuario | None:
    return (
        db.query(Usuario)
        .filter(
            Usuario.departamento_id == departamento_id,
            Usuario.rol == RolUsuario.encargado_area,
            Usuario.activo == True,  # noqa: E712
        )
        .first()
    )


def _asignar_por_ia(db: Session, idea: Idea, departamentos: list[Departamento]) -> dict | None:
    if not departamentos:
        return None
    try:
        historial = _historial_para_ia(db, idea.id)
        return asignar_revisor_ia(
            historial=historial,
            titulo=idea.titulo,
            sugerencia_autor=idea.sugerencia_revisor_autor,
            motivo_autor=idea.motivo_sugerencia_revisor_autor,
            nombres_departamentos=[d.nombre for d in departamentos],
        )
    except Exception:
        # Cualquier fallo inesperado (no solo de la API, que
        # asignar_revisor_ia ya maneja internamente) degrada al fallback
        # de mismo departamento del autor, nunca rompe el envío de la idea.
        logger.exception("asignacion automatica de revisor fallo para idea %s", idea.id)
        return None


def crear_revision_para_idea(db: Session, idea: Idea) -> RevisionIdea:
    departamentos = db.query(Departamento).all()
    resultado_ia = _asignar_por_ia(db, idea, departamentos)

    revisor = None
    departamento_sugerido_id = None
    justificacion_ia = None
    acepto_sugerencia_autor = None

    if resultado_ia is not None:
        departamento_ia = next(
            (d for d in departamentos if d.nombre == resultado_ia["departamento"]), None
        )
        if departamento_ia is not None:
            departamento_sugerido_id = departamento_ia.id
            justificacion_ia = resultado_ia["justificacion"]
            # acepto_sugerencia_autor solo es significativo si el autor dio
            # una sugerencia real que evaluar — si no, queda None (no False).
            if idea.sugerencia_revisor_autor is not None:
                acepto_sugerencia_autor = resultado_ia["acepto_sugerencia_autor"]
            revisor = _buscar_encargado_activo(db, departamento_ia.id)

    if revisor is None and idea.autor.departamento_id is not None:
        # Fallback: mismo departamento del autor (comportamiento original),
        # ya sea porque la IA falló o porque el departamento que sugirió no
        # tiene ningún encargado_area activo todavía.
        revisor = _buscar_encargado_activo(db, idea.autor.departamento_id)

    ahora = datetime.now(timezone.utc)
    revision = RevisionIdea(
        idea_id=idea.id,
        revisor_id=revisor.id if revisor else None,
        estado=EstadoRevision.pendiente_revision if revisor else EstadoRevision.pendiente_asignacion,
        fecha_asignacion=ahora if revisor else None,
        departamento_sugerido_ia_id=departamento_sugerido_id,
        justificacion_ia=justificacion_ia,
        acepto_sugerencia_autor=acepto_sugerencia_autor,
    )
    db.add(revision)
    return revision
