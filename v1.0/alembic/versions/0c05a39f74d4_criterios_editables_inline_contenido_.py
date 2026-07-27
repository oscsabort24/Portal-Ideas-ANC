"""criterios editables inline contenido descripcion

Revision ID: 0c05a39f74d4
Revises: 7c1e9a4d2f8b
Create Date: 2026-07-23 01:09:22.740778

Agrega texto editable (`contenido`) y explicación corta (`descripcion`) a
DocumentoCriterio, más `actualizado_por_id`/`actualizado_en` para trackear
ediciones inline (PATCH /criterios/{id}) SEPARADO de `subido_por`/`subido_en`
(que siguen marcando la subida del archivo original) — ver criterios/models.py
para el razonamiento completo de por qué la edición inline NO crea una
versión nueva.

BACKFILL: para las filas activas existentes cuyo archivo es .docx, se
extrae el texto con python-docx (misma lógica que
clasificacion/service.py:_extraer_texto_docx) y se persiste en `contenido`
para que ya se pueda ver/editar sin tener que volver a subir el archivo.
Los criterios activos que sean .pdf quedan con `contenido=NULL` — no hay
librería de extracción de PDF instalada en el proyecto (decisión: no
agregar una dependencia nueva solo para esto, ver conversación); el admin
pega el texto manualmente la primera vez que edite ese criterio.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c05a39f74d4'
down_revision: Union[str, Sequence[str], None] = '7c1e9a4d2f8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documentos_criterio", sa.Column("contenido", sa.Unicode(), nullable=True))
    op.add_column("documentos_criterio", sa.Column("descripcion", sa.Unicode(length=500), nullable=True))
    op.add_column("documentos_criterio", sa.Column("actualizado_por_id", sa.Integer(), nullable=True))
    op.add_column("documentos_criterio", sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_documentos_criterio_actualizado_por_id_usuarios",
        "documentos_criterio",
        "usuarios",
        ["actualizado_por_id"],
        ["id"],
    )

    if not op.get_context().as_sql:
        # El backfill hace SELECT/lee archivos reales — no tiene sentido
        # (ni es posible) en modo `--sql` offline, solo al aplicar de verdad.
        _backfill_contenido_docx()


def _backfill_contenido_docx() -> None:
    from docx import Document

    conexion = op.get_bind()
    filas = conexion.execute(
        sa.text(
            "SELECT id, ruta_archivo FROM documentos_criterio "
            "WHERE activo = 1 AND ruta_archivo LIKE '%.docx'"
        )
    ).fetchall()

    for fila in filas:
        try:
            documento = Document(fila.ruta_archivo)
            texto = "\n".join(p.text for p in documento.paragraphs if p.text.strip())
        except Exception:
            # Archivo movido/corrupto: se deja igual que un .pdf (contenido
            # NULL, editable manualmente) en vez de romper la migración.
            continue
        if texto:
            conexion.execute(
                sa.text("UPDATE documentos_criterio SET contenido = :contenido WHERE id = :id"),
                {"contenido": texto, "id": fila.id},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_documentos_criterio_actualizado_por_id_usuarios", "documentos_criterio", type_="foreignkey")
    op.drop_column("documentos_criterio", "actualizado_en")
    op.drop_column("documentos_criterio", "actualizado_por_id")
    op.drop_column("documentos_criterio", "descripcion")
    op.drop_column("documentos_criterio", "contenido")
