"""permisos por rol configurables: tabla permisos_rol + seed exacto del comportamiento actual

Revision ID: 4d81f6c93a52
Revises: 6dc0dd4b262d
Create Date: 2026-08-18

CONTEXTO: ver diseno-pendiente/fase-permisos-por-rol.md.preview (diseño
aprobado). Migra a una tabla configurable SOLO los checks de rol puro
catalogados como MIGRA en ese documento (4 permisos: ve_todas_las_ideas,
ve_flow_control, es_revisor_elegible, corrige_clasificacion). Los checks
relacionales (ser autor, ser el revisor asignado, ser miembro de un CAB
específico) NO se tocan — siguen en el código tal cual están hoy.

CERO CAMBIO DE COMPORTAMIENTO: el seed de abajo replica exactamente lo
que cada rol puede hacer hoy sin esta tabla.

admin NO tiene filas a propósito (excepción deliberada, no configurable):
el código sigue comprobando `usuario.rol == admin` como bypass, nunca
consulta esta tabla para admin.
"""
from alembic import op
import sqlalchemy as sa

revision = "4d81f6c93a52"
down_revision = "6dc0dd4b262d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permisos_rol",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rol",
            sa.Enum("colaborador", "encargado_area", "gerente", "admin", name="rol_usuario"),
            nullable=False,
        ),
        sa.Column(
            "clave_permiso",
            sa.Enum(
                "ve_todas_las_ideas",
                "ve_flow_control",
                "es_revisor_elegible",
                "corrige_clasificacion",
                name="clave_permiso",
            ),
            nullable=False,
        ),
        sa.Column("permitido", sa.Boolean(), nullable=False, server_default=sa.true()),
        # Nullable a propósito: NULL = fila de seed, nunca editada por una
        # persona todavía — mismo criterio que actualizado_por_id/
        # actualizado_en ya usaban en documentos_criterio (ver
        # criterios/models.py) para distinguir "así vino" de "alguien lo tocó".
        sa.Column("actualizado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("rol", "clave_permiso", name="uq_permiso_rol_clave"),
    )

    permisos_rol = sa.table(
        "permisos_rol",
        sa.column("rol", sa.String),
        sa.column("clave_permiso", sa.String),
        sa.column("permitido", sa.Boolean),
    )
    op.bulk_insert(
        permisos_rol,
        [
            # gerente: replica ROLES_VEN_TODAS_LAS_IDEAS (ideas/router.py:70),
            # requerir_admin_o_gerente (usuarios/dependencies.py:103-109), y
            # ROLES_HABILITADOS_REVISOR (revision/service.py:31 + revision/router.py:16-20)
            {"rol": "gerente", "clave_permiso": "ve_todas_las_ideas", "permitido": True},
            {"rol": "gerente", "clave_permiso": "ve_flow_control", "permitido": True},
            {"rol": "gerente", "clave_permiso": "es_revisor_elegible", "permitido": True},
            # encargado_area: replica ROLES_HABILITADOS_REVISOR, mismo origen que gerente arriba
            {"rol": "encargado_area", "clave_permiso": "es_revisor_elegible", "permitido": True},
            # colaborador: sin filas — hoy no tiene ninguno de estos 4 permisos
            # corrige_clasificacion: sin filas para NINGÚN rol configurable —
            # hoy es admin-only sin excepción (clasificacion/router.py:16-20,
            # decisión de negocio explícita), el catálogo lo incluye para que
            # sea configurable a futuro SIN requerir otra migración, no
            # porque alguien lo tenga hoy.
        ],
    )


def downgrade() -> None:
    op.drop_table("permisos_rol")
