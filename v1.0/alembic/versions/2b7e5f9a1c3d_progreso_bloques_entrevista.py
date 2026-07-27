"""progreso_bloques en ideas — checklist de los 5 bloques de la entrevista

Revision ID: 2b7e5f9a1c3d
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-22

Agrega una columna JSON nullable (almacenada como NVARCHAR(MAX) en SQL
Server vía el tipo genérico sa.JSON — no existe un tipo JSON nativo en el
dialecto mssql, pero sa.JSON serializa/deserializa igual sobre texto) con
el último estado de cada uno de los 5 bloques obligatorios de la
entrevista, para el checklist visual del frontend (ver
core/claude_client.py:ProgresoBloques). Columna nueva y nullable — no
requiere backfill, las ideas existentes simplemente quedan con
progreso_bloques = NULL hasta su próximo mensaje de entrevista.
"""
from alembic import op
import sqlalchemy as sa

revision = "2b7e5f9a1c3d"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("progreso_bloques", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ideas", "progreso_bloques")
