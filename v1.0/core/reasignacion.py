"""Política compartida de reasignación con aceptación/rechazo — usada por
revision/ y comites/ (ver diseno-pendiente/cab-departamento-reasignacion.md.preview).

Generalizado desde el diseño original de Fase 4 (pensado solo para
RevisionIdea): MixinReasignacion define las 4 columnas de estado
compartidas, y las funciones reciben el modelo/campo "responsable actual"
en vez de tener RevisionIdea/EstadoRevision hardcodeados.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

DIAS_HABILES_ACEPTACION_REASIGNACION = 3
MAX_RECHAZOS_CONSECUTIVOS = 2


class MixinReasignacion:
    """4 columnas del ciclo propuesta -> aceptación/rechazo, compartidas
    entre RevisionIdea y ComiteIdea. Quien es "el responsable actual" NO
    vive acá — cada tabla mantiene su propio nombre (RevisionIdea.revisor_id,
    ComiteIdea.asignado_a_id) porque tiene semántica propia en cada
    contexto; las funciones de este módulo lo reciben como parámetro
    (`campo_responsable`).
    """

    @declared_attr
    def propuesto_a_id(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("usuarios.id"), nullable=True)

    @declared_attr
    def reasignacion_solicitada_por_id(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("usuarios.id"), nullable=True)

    @declared_attr
    def fecha_solicitud_reasignacion(cls) -> Mapped[datetime | None]:
        from sqlalchemy import DateTime

        return mapped_column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def rechazos_reasignacion_consecutivos(cls) -> Mapped[int]:
        return mapped_column(Integer, default=0, server_default="0", nullable=False)

    @declared_attr
    def propuesto_a(cls):
        return relationship("Usuario", foreign_keys=[cls.propuesto_a_id])

    @declared_attr
    def reasignacion_solicitada_por(cls):
        return relationship("Usuario", foreign_keys=[cls.reasignacion_solicitada_por_id])


def obtener_bloqueado_para_reasignar(db, modelo, idea_id: int):
    """Fetch de la fila `idea_id` en `modelo` (RevisionIdea o ComiteIdea) con
    lock de fila — usar SIEMPRE en el endpoint de "proponer reasignación"
    (revision/router.py:reasignar, comites/router.py:reasignar) en vez de un
    query plano.

    NO usa `.with_for_update()`: T-SQL no tiene una cláusula FOR UPDATE
    estándar, y el dialecto mssql de SQLAlchemy IGNORA `.with_for_update()`
    en silencio (sin error, sin warning) — se comprobó en vivo compilando el
    query contra `mssql.dialect()`: el SQL generado no cambia en absoluto,
    y una prueba con 2 hilos concurrentes confirmó que ambos pisaban la
    misma fila sin ningún bloqueo. El lock real en SQL Server requiere un
    hint de tabla explícito vía `.with_hint(modelo, "WITH (UPDLOCK, ROWLOCK)",
    "mssql")` — UPDLOCK toma un lock de escritura desde el SELECT (no solo
    en el UPDATE posterior), ROWLOCK evita que SQL Server escale el lock a
    nivel de página/tabla.

    Sin este lock, dos propuestas de reasignación casi simultáneas sobre la
    misma idea podían pasar ambas el chequeo `estado == pendiente` antes de
    que la primera hiciera commit — la segunda pisaba en silencio
    propuesto_a_id/reasignacion_solicitada_por_id de la primera, sin error ni
    aviso a nadie. Mismo problema de fondo que
    clasificacion/service.py:crear_clasificacion_para_idea ya resuelve para
    doble-aprobación (ahí con re-query + reutilización de fila, porque el
    conflicto es un INSERT contra un UNIQUE constraint; acá es un UPDATE
    contra el mismo row, así que el fix correcto es un lock de fila, no un
    re-query).

    Con este lock, la segunda request queda bloqueada hasta que la primera
    termine su transacción (commit o rollback) y, al reanudar, ve el estado
    YA actualizado por la primera — el chequeo `if entidad.estado != ...`
    que sigue después de este fetch la rechaza limpiamente con un 400 en vez
    de sobreescribir nada."""
    return (
        db.query(modelo)
        .filter_by(idea_id=idea_id)
        .with_hint(modelo, "WITH (UPDLOCK, ROWLOCK)", "mssql")
        .first()
    )


def sumar_dias_habiles(desde: datetime, dias: int) -> datetime:
    resultado = desde
    restantes = dias
    while restantes > 0:
        resultado += timedelta(days=1)
        if resultado.weekday() < 5:
            restantes -= 1
    return resultado


def aplicar_rechazo_reasignacion(
    db,
    entidad: Any,
    *,
    campo_responsable: str,
    estado_sin_asignar,
    estado_normal,
    idea_id: int,
    actor_id: int,
    tipo_evento,
    detalle: str | None = None,
) -> None:
    """Política única de rechazo — compartida por rechazo explícito y expiración.

    Primer rechazo: vuelve al estado normal, el responsable actual no
    cambia (nunca se movió mientras la propuesta estaba pendiente).
    Segundo rechazo consecutivo: se limpia el responsable — si
    `estado_sin_asignar` existe (RevisionIdea: pendiente_asignacion), cae
    ahí; si no (ComiteIdea, que no tiene un estado bloqueante
    equivalente), simplemente vuelve al estado normal sin responsable
    específico, visible a cualquiera del departamento otra vez.
    """
    from ideas.models import HistorialIdea

    db.add(
        HistorialIdea(
            idea_id=idea_id,
            tipo_evento=tipo_evento,
            actor_id=actor_id,
            sujeto_id=entidad.propuesto_a_id,
            detalle=detalle,
        )
    )

    entidad.rechazos_reasignacion_consecutivos += 1
    entidad.propuesto_a_id = None
    entidad.reasignacion_solicitada_por_id = None
    entidad.fecha_solicitud_reasignacion = None

    if entidad.rechazos_reasignacion_consecutivos >= MAX_RECHAZOS_CONSECUTIVOS:
        setattr(entidad, campo_responsable, None)
        entidad.estado = estado_sin_asignar if estado_sin_asignar is not None else estado_normal
    else:
        entidad.estado = estado_normal


def expirar_reasignaciones_vencidas(
    db,
    modelo,
    *,
    estado_pendiente_aceptacion,
    campo_responsable: str,
    estado_sin_asignar,
    estado_normal,
    tipo_evento_expirada,
) -> list:
    ahora = datetime.now(timezone.utc)
    pendientes = (
        db.query(modelo)
        .filter(
            modelo.estado == estado_pendiente_aceptacion,
            modelo.fecha_solicitud_reasignacion.isnot(None),
        )
        .all()
    )

    expiradas = []
    for entidad in pendientes:
        limite = sumar_dias_habiles(entidad.fecha_solicitud_reasignacion, DIAS_HABILES_ACEPTACION_REASIGNACION)
        if ahora < limite:
            continue
        aplicar_rechazo_reasignacion(
            db,
            entidad,
            campo_responsable=campo_responsable,
            estado_sin_asignar=estado_sin_asignar,
            estado_normal=estado_normal,
            idea_id=entidad.idea_id,
            actor_id=entidad.reasignacion_solicitada_por_id or getattr(entidad, campo_responsable),
            tipo_evento=tipo_evento_expirada,
            detalle=f"Sin respuesta en {DIAS_HABILES_ACEPTACION_REASIGNACION} días hábiles",
        )
        expiradas.append(entidad)
    return expiradas
