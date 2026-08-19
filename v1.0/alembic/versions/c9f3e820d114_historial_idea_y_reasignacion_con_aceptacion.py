"""historial_idea + reasignación con aceptación (revision_ideas)

Revision ID: c9f3e820d114
Revises: b4d17c9e5a20
Create Date: 2026-08-19

Cuatro cambios:
1. Nuevo valor `pendiente_aceptacion_reasignacion` en el enum de estado
   de revisión (CHECK constraint recreado).
2. Columnas de propuesta en `revision_ideas`: propuesto_a_id (nombrada
   así, no `revisor_propuesto_id`, para que el mismo nombre sirva en
   comite_ideas — ver core/reasignacion.py:MixinReasignacion),
   reasignacion_solicitada_por_id, fecha_solicitud_reasignacion,
   rechazos_reasignacion_consecutivos.
3. Tabla `historial_idea` + enum `tipo_evento_idea`.
4. Backfill de historial_idea desde historial_reasignacion (eventos
   reasignacion_aceptada, ya que bajo el modelo viejo la reasignación se
   aplicaba de inmediato).
"""
from alembic import op
import sqlalchemy as sa

revision = "c9f3e820d114"
down_revision = "b4d17c9e5a20"
branch_labels = None
depends_on = None

TIPO_EVENTO_IDEA = sa.Enum(
    "reasignacion_solicitada",
    "reasignacion_aceptada",
    "reasignacion_rechazada",
    "reasignacion_expirada",
    name="tipo_evento_idea",
)

ESTADOS_NUEVOS = (
    "pendiente_asignacion",
    "pendiente_revision",
    "aprobada",
    "cambios_solicitados",
    "pendiente_aceptacion_reasignacion",
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
    # La columna nació VARCHAR(20) — insuficiente para
    # 'pendiente_aceptacion_reasignacion' (34 caracteres). Sin este ALTER,
    # el primer UPDATE con ese valor falla con "String or binary data
    # would be truncated" aunque el CHECK ya lo permita.
    op.alter_column("revision_ideas", "estado", existing_type=sa.String(20), type_=sa.String(40), nullable=False)
    _recrear_check_estado(ESTADOS_NUEVOS)

    op.add_column("revision_ideas", sa.Column("propuesto_a_id", sa.Integer(), nullable=True))
    op.add_column(
        "revision_ideas", sa.Column("reasignacion_solicitada_por_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "revision_ideas",
        sa.Column("fecha_solicitud_reasignacion", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "revision_ideas",
        sa.Column("rechazos_reasignacion_consecutivos", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_revision_ideas_propuesto_a", "revision_ideas", "usuarios", ["propuesto_a_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_revision_ideas_reasignacion_solicitada_por",
        "revision_ideas", "usuarios", ["reasignacion_solicitada_por_id"], ["id"],
    )

    op.create_table(
        "historial_idea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idea_id", sa.Integer(), nullable=False),
        sa.Column("tipo_evento", TIPO_EVENTO_IDEA, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("sujeto_id", sa.Integer(), nullable=True),
        sa.Column("detalle", sa.Unicode(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["sujeto_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historial_idea_idea_id", "historial_idea", ["idea_id"])

    op.execute(
        """
        INSERT INTO historial_idea (idea_id, tipo_evento, actor_id, sujeto_id, detalle, creado_en)
        SELECT r.idea_id,
               'reasignacion_aceptada',
               h.revisor_anterior_id,
               h.revisor_nuevo_id,
               N'Migrado de historial_reasignacion: bajo el modelo anterior la reasignacion se aplicaba sin aceptacion explicita',
               h.creada_en
          FROM historial_reasignacion h
          JOIN revision_ideas r ON r.id = h.revision_id
         ORDER BY h.creada_en
        """
    )


def downgrade() -> None:
    op.drop_index("ix_historial_idea_idea_id", table_name="historial_idea")
    op.drop_table("historial_idea")
    op.drop_constraint("fk_revision_ideas_reasignacion_solicitada_por", "revision_ideas", type_="foreignkey")
    op.drop_constraint("fk_revision_ideas_propuesto_a", "revision_ideas", type_="foreignkey")
    op.drop_column("revision_ideas", "rechazos_reasignacion_consecutivos")
    op.drop_column("revision_ideas", "fecha_solicitud_reasignacion")
    op.drop_column("revision_ideas", "reasignacion_solicitada_por_id")
    op.drop_column("revision_ideas", "propuesto_a_id")

    op.execute(
        "UPDATE revision_ideas SET estado = 'pendiente_revision' "
        "WHERE estado = 'pendiente_aceptacion_reasignacion'"
    )
    _recrear_check_estado(ESTADOS_VIEJOS)
    op.alter_column("revision_ideas", "estado", existing_type=sa.String(40), type_=sa.String(20), nullable=False)
