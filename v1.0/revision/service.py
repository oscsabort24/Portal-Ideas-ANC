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

NOTA sobre Fase 3 (ResponsableArea): la tabla existe (ver
usuarios/models.py:ResponsableArea) pero _buscar_encargado_activo NO la
usa todavía — sigue resolviendo por departamento+rol directamente, a
propósito, porque la tabla nace vacía sin el seed de datos reales del
negocio. Cuando ese seed exista, este es el único punto a cambiar.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.claude_client import _CRITERIOS_ASIGNACION_REVISOR_DEFAULT, asignar_revisor_ia
from core.reasignacion import aplicar_rechazo_reasignacion as _aplicar_rechazo_generico
from core.reasignacion import expirar_reasignaciones_vencidas as _expirar_generico
from criterios.models import CriterioIA, TipoCriterio
from ideas.models import Idea, TipoEventoIdea
from ideas.service import historial_para_ia
from permisos.models import ClavePermiso
from permisos.service import rol_tiene_permiso
from revision.models import EstadoRevision, OrigenAsignacion, RevisionIdea
from usuarios.models import Departamento, RolUsuario, Usuario

logger = logging.getLogger(__name__)


def _roles_habilitados_revisor(db: Session) -> list[RolUsuario]:
    """Roles con el permiso configurable es_revisor_elegible — mismo
    criterio usado en revision/router.py:_validar_revisor_destino
    (asignar/reasignar manual). admin siempre incluido vía bypass de
    rol_tiene_permiso."""
    return [rol for rol in RolUsuario if rol_tiene_permiso(db, rol, ClavePermiso.es_revisor_elegible)]


def _buscar_encargado_activo(
    db: Session, departamento_id: int, excluir_usuario_id: int | None = None
) -> Usuario | None:
    """`excluir_usuario_id` es el AUTOR de la idea: nadie revisa lo suyo.

    Sin esta exclusión, un autor con rol elegible en el departamento elegido
    y el id más bajo se asignaba su propia idea — y como el criterio de
    desempate es `id` ascendente, no era aleatorio: pasaba siempre para esa
    persona. Se encontraron 2 revisiones así en la BD (ideas 22 y 25), las dos
    ya aprobadas por el propio autor.

    Se excluye acá y no en el llamador para que ningún camino de asignación
    automática pueda olvidarse: los dos (sugerencia de IA y fallback por
    departamento del autor) pasan por esta función.
    """
    # ORDER BY Usuario.id: sin esto, con más de un usuario elegible activo en
    # el mismo departamento, el resultado dependía del plan de ejecución de
    # SQL Server (no determinístico) — se reprodujo en vivo el 19/8/2026 con
    # los ids 4 (admin) y 6 (Armando) en el mismo departamento. No hay un
    # campo de antigüedad en Usuario, así que id ascendente (= orden de alta)
    # es el proxy determinístico más simple; no es la solución definitiva —
    # esa es activar ResponsableArea (Fase 3, ver nota del módulo arriba)
    # cuando exista el seed real de datos del negocio.
    query = db.query(Usuario).filter(
        Usuario.departamento_id == departamento_id,
        Usuario.rol.in_(_roles_habilitados_revisor(db)),
        Usuario.activo == True,  # noqa: E712
    )
    if excluir_usuario_id is not None:
        query = query.filter(Usuario.id != excluir_usuario_id)
    return query.order_by(Usuario.id.asc()).first()


def _criterio_asignacion_revisor(db: Session) -> str:
    """Texto activo de CriterioIA(tipo=asignacion_revisor) — antes de este
    cambio, asignar_revisor_ia ignoraba lo que un admin subiera en
    criterios/ y usaba siempre la constante hardcodeada
    _CRITERIOS_ASIGNACION_REVISOR_DEFAULT, un bug real (el criterio se
    guardaba pero nunca se usaba). Se mantiene ese default solo como
    respaldo para el momento en que todavía no exista ninguna fila activa."""
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
        historial = historial_para_ia(db, idea.id)
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


def aplicar_rechazo_reasignacion(
    db: Session, revision: RevisionIdea, *, actor_id: int, tipo_evento: TipoEventoIdea, detalle: str | None = None
) -> None:
    """Wrapper sobre core/reasignacion.py con los parámetros propios de
    RevisionIdea — segundo rechazo consecutivo suelta al pool
    (pendiente_asignacion, revisor_id=None) para que un admin decida."""
    _aplicar_rechazo_generico(
        db,
        revision,
        campo_responsable="revisor_id",
        estado_sin_asignar=EstadoRevision.pendiente_asignacion,
        estado_normal=EstadoRevision.pendiente_revision,
        idea_id=revision.idea_id,
        actor_id=actor_id,
        tipo_evento=tipo_evento,
        detalle=detalle,
    )
    if revision.estado == EstadoRevision.pendiente_asignacion:
        revision.origen_asignacion = OrigenAsignacion.sin_asignar


def expirar_reasignaciones_vencidas(db: Session) -> list[RevisionIdea]:
    return _expirar_generico(
        db,
        RevisionIdea,
        estado_pendiente_aceptacion=EstadoRevision.pendiente_aceptacion_reasignacion,
        campo_responsable="revisor_id",
        estado_sin_asignar=EstadoRevision.pendiente_asignacion,
        estado_normal=EstadoRevision.pendiente_revision,
        tipo_evento_expirada=TipoEventoIdea.reasignacion_expirada,
    )


def crear_revision_para_idea(db: Session, idea: Idea) -> RevisionIdea:
    departamentos = db.query(Departamento).all()
    resultado_ia = _asignar_por_ia(db, idea, departamentos)

    revisor = None
    departamento_sugerido_id = None
    justificacion_ia = None
    acepto_sugerencia_autor = None
    origen = OrigenAsignacion.sin_asignar

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
            revisor = _buscar_encargado_activo(db, departamento_ia.id, excluir_usuario_id=idea.autor_id)
            if revisor is not None:
                origen = OrigenAsignacion.mapeo_area

    if revisor is None and idea.autor.departamento_id is not None:
        # Fallback: mismo departamento del autor (comportamiento original),
        # ya sea porque la IA falló o porque el departamento que sugirió no
        # tiene ningún usuario con rol habilitado para revisar activo todavía.
        revisor = _buscar_encargado_activo(
            db, idea.autor.departamento_id, excluir_usuario_id=idea.autor_id
        )
        if revisor is not None:
            origen = OrigenAsignacion.fallback_departamento_autor

    ahora = datetime.now(timezone.utc)
    revision = RevisionIdea(
        idea_id=idea.id,
        revisor_id=revisor.id if revisor else None,
        estado=EstadoRevision.pendiente_revision if revisor else EstadoRevision.pendiente_asignacion,
        fecha_asignacion=ahora if revisor else None,
        departamento_sugerido_ia_id=departamento_sugerido_id,
        justificacion_ia=justificacion_ia,
        acepto_sugerencia_autor=acepto_sugerencia_autor,
        origen_asignacion=origen,
    )
    db.add(revision)
    return revision
