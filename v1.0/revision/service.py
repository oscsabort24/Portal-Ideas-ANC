"""Lógica de asignación de revisión, llamada desde ideas/router.py cuando una idea se envía.

*** ASIGNACIÓN AUTOMÁTICA POR IA, CON FALLBACK ***
Se intenta primero que la IA sugiera, a partir del CONTENIDO real de la
idea (no solo el departamento del autor), a qué departamento le
corresponde revisarla — considerando también, si existe, una sugerencia
opcional del autor (ver asignar_revisor_ia en core/claude_client.py).

Si la IA falla por cualquier motivo, o si el departamento que sugiere no
tiene ningún usuario con rol habilitado para revisar activo, se cae al
comportamiento original: mismo departamento del autor. Si tampoco hay
nadie ahí, la idea queda "pendiente_asignacion" para que un admin la
asigne manualmente. Esto NUNCA debe romper el envío de la idea.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.claude_client import _CRITERIOS_ASIGNACION_REVISOR_DEFAULT, asignar_revisor_ia
from criterios.models import CriterioIA, TipoCriterio
from ideas.models import Idea, MensajeEntrevista
from permisos.models import ClavePermiso
from permisos.service import rol_tiene_permiso
from revision.models import EstadoRevision, RevisionIdea
from usuarios.models import Departamento, RolUsuario, Usuario

logger = logging.getLogger(__name__)


def _roles_habilitados_revisor(db: Session) -> list[RolUsuario]:
    """Roles con el permiso configurable es_revisor_elegible — mismo
    criterio usado en revision/router.py:_validar_revisor_destino
    (asignar/reasignar manual). admin siempre incluido vía bypass de
    rol_tiene_permiso."""
    return [rol for rol in RolUsuario if rol_tiene_permiso(db, rol, ClavePermiso.es_revisor_elegible)]


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
            Usuario.rol.in_(_roles_habilitados_revisor(db)),
            Usuario.activo == True,  # noqa: E712
        )
        .first()
    )


def _criterio_asignacion_revisor(db: Session) -> str:
    """Texto activo de CriterioIA(tipo=asignacion_revisor) — antes de este
    cambio, asignar_revisor_ia ignoraba lo que un admin subiera en
    criterios/ y usaba siempre la constante hardcodeada
    _CRITERIOS_ASIGNACION_REVISOR_DEFAULT, un bug real (el criterio se
    guardaba pero nunca se usaba). Se mantiene ese default solo como
    respaldo para el momento en que todavía no exista ninguna fila activa
    (ej. justo después de aplicar la migración de criterios_ia)."""
    criterio = (
        db.query(CriterioIA)
        .filter_by(tipo=TipoCriterio.asignacion_revisor, departamento_id=None, activo=True)
        .first()
    )
    return criterio.contenido if criterio else _CRITERIOS_ASIGNACION_REVISOR_DEFAULT


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
            criterio_texto=_criterio_asignacion_revisor(db),
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
        # tiene ningún usuario con rol habilitado para revisar activo todavía.
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
