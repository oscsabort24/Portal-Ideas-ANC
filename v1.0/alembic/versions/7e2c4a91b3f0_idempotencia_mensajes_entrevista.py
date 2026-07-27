"""idempotency_key en mensajes_entrevista — evita el turno duplicado al reintentar

Revision ID: 7e2c4a91b3f0
Revises: 0c05a39f74d4
Create Date: 2026-07-27

POST /ideas/{id}/mensajes no era idempotente: el frontend aborta el fetch a
los 40s (ChatEntrevista.tsx:TIMEOUT_ENVIO_MS) pero abortar el cliente NO
cancela la transacción del servidor, así que si el turno de IA tardaba más
el mensaje ya estaba guardado. El usuario reintentaba —el propio mensaje de
error se lo pide— y quedaban dos mensajes de usuario idénticos con dos
turnos de IA.

La columna es nullable y sin backfill: todo el historial previo, y todos
los mensajes de rol=asistente, quedan en NULL.

El índice es FILTRADO a propósito. Un UNIQUE normal en SQL Server considera
iguales entre sí a todos los NULL y solo dejaría existir una fila sin
clave, lo que reventaría contra las filas existentes. Con `WHERE
idempotency_key IS NOT NULL` la unicidad aplica solo donde hay clave real.
"""
from alembic import op
import sqlalchemy as sa

revision = "7e2c4a91b3f0"
down_revision = "0c05a39f74d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mensajes_entrevista",
        sa.Column("idempotency_key", sa.Unicode(length=64), nullable=True),
    )
    op.create_index(
        "uq_mensaje_idea_idempotency_key",
        "mensajes_entrevista",
        ["idea_id", "idempotency_key"],
        unique=True,
        mssql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_mensaje_idea_idempotency_key", table_name="mensajes_entrevista")
    op.drop_column("mensajes_entrevista", "idempotency_key")
