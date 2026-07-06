"""modelos iniciales usuarios

Revision ID: 71b48f37f615
Revises:
Create Date: 2026-07-06

Escrita a mano: no hay instancia de SQL Server disponible en este entorno
para correr --autogenerate contra una base real. Refleja exactamente los
modelos definidos en usuarios/models.py. Se recomienda revisarla contra
una base de desarrollo real antes de aplicarla en un ambiente compartido.
"""

from alembic import op
import sqlalchemy as sa

revision = "71b48f37f615"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departamentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False, unique=True),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("correo", sa.String(200), nullable=False, unique=True),
        sa.Column(
            "rol",
            sa.Enum("colaborador", "encargado_area", "gerente", "admin", name="rol_usuario"),
            nullable=False,
            server_default="colaborador",
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departamentos.id"), nullable=True),
        sa.Column("reporta_a_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
    )

    op.create_table(
        "miembros_cab",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column(
            "tipo_cab",
            sa.Enum("innovacion", "transformacion_digital", name="tipo_cab"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("miembros_cab")
    op.drop_table("usuarios")
    op.drop_table("departamentos")
