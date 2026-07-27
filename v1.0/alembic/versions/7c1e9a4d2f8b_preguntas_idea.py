"""preguntas hechas sobre una idea (revision y comite)

Revision ID: 7c1e9a4d2f8b
Revises: 2b7e5f9a1c3d
Create Date: 2026-07-23

Tabla nueva, append-only, mismo patrón que historial_retroalimentacion /
historial_reasignacion — bitácora de cada POST /ideas/{id}/preguntar (ver
ideas/router.py:preguntar). FK directo a ideas.id (no a revision_ideas.id)
porque también se lee desde CAB (ver ideas/router.py:obtener_resumen), que
no tiene fila propia en revision_ideas.

Las columnas de texto libre (pregunta, respuesta) se crean directo como
NVARCHAR(MAX) — no VARCHAR/TEXT — para no repetir el bug de encoding que
tuvo que corregirse después en la migración 1a2b3c4d5e6f (ver esa
migración para el contexto completo del problema de CP1252 vs UTF-16).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

revision = "7c1e9a4d2f8b"
down_revision = "2b7e5f9a1c3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preguntas_idea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idea_id", sa.Integer(), nullable=False),
        sa.Column("origen", sa.Enum("revision", "comite", name="origen_pregunta"), nullable=False),
        sa.Column("pregunta", mssql.NVARCHAR(None), nullable=False),
        sa.Column("respuesta", mssql.NVARCHAR(None), nullable=False),
        sa.Column("preguntada_por_id", sa.Integer(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["preguntada_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # sa.Enum en mssql se implementa como CHECK constraint inline en la
    # columna (no como un tipo aparte, a diferencia de Postgres) — dropear
    # la tabla ya limpia todo, sin necesitar un DROP TYPE separado. Mismo
    # patrón que 8601a283f177 (RiceEvaluacion.impacto/confianza/etc.).
    op.drop_table("preguntas_idea")
