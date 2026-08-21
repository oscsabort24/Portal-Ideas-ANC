"""rechazo final de revisión por el encargado de área

Revision ID: d5e8f21a9c36
Revises: a3f7c9e21d68
Create Date: 2026-08-22

Nuevo valor 'rechazada' en el enum de estado de revisión (CHECK
constraint recreado, mismo patrón que c9f3e820d114) + columna
motivo_rechazo en revision_ideas — mismo patrón que
ComiteIdea.motivo_rechazo, para que el encargado de área pueda
rechazar una idea de forma final (Opción A del diseño de "4ta acción
del revisor", ver diseno-pendiente/apelacion-rechazo-revisor.md.preview
para la Opción C descartada por ahora).

No se amplía el VARCHAR de la columna (ya es VARCHAR(40) desde
c9f3e820d114) — 'rechazada' (9 caracteres) entra sin problema.
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e8f21a9c36"
down_revision = "a3f7c9e21d68"
branch_labels = None
depends_on = None

ESTADOS_NUEVOS = (
    "pendiente_asignacion",
    "pendiente_revision",
    "aprobada",
    "cambios_solicitados",
    "pendiente_aceptacion_reasignacion",
    "rechazada",
)
ESTADOS_VIEJOS = ESTADOS_NUEVOS[:-1]


def _recrear_check_estado(estados: tuple[str, ...]) -> None:
    op.execute(
        """
        DECLARE @nombre sysname;
        SELECT @nombre = cc.name
          FROM sys.check_constraints cc
          JOIN sys.columns c
            ON c.object_id = cc.parent_object_id
           AND c.column_id = cc.parent_column_id
         WHERE cc.parent_object_id = OBJECT_ID('revision_ideas')
           AND c.name = 'estado';
        IF @nombre IS NOT NULL
            EXEC('ALTER TABLE revision_ideas DROP CONSTRAINT [' + @nombre + ']');
        """
    )
    valores = ", ".join(f"'{e}'" for e in estados)
    op.execute(
        f"ALTER TABLE revision_ideas ADD CONSTRAINT ck_revision_ideas_estado "
        f"CHECK (estado IN ({valores}))"
    )


def upgrade() -> None:
    _recrear_check_estado(ESTADOS_NUEVOS)
    op.add_column("revision_ideas", sa.Column("motivo_rechazo", sa.Unicode(), nullable=True))


def downgrade() -> None:
    """ADVERTENCIA: cualquier RevisionIdea en estado 'rechazada' al
    momento del downgrade queda en un estado que el CHECK viejo no
    permite — resolver esas filas (ej. volver a pendiente_revision)
    antes de correr este downgrade."""
    op.drop_column("revision_ideas", "motivo_rechazo")
    _recrear_check_estado(ESTADOS_VIEJOS)
