"""rol=revisor en mensajes_entrevista + columna usuario_id

Revision ID: b8d3f57a2c41
Revises: f2a6d1c73e84
Create Date: 2026-08-26

Cuando un revisor de área pide cambios, su comentario se guarda como un
MensajeEntrevista para que aparezca en el chat del autor
(revision/router.py:pedir_cambios). Hasta ahora se guardaba con
rol='asistente', lo que producía dos problemas:

  1. El autor lo veía como si lo hubiera escrito la IA — BurbujaMensaje solo
     distinguía usuario vs no-usuario, sin nombre ni estilo propio.
  2. Volvía al modelo en el turno siguiente como texto del asistente, así que
     la IA continuaba la conversación creyendo que ella lo había dicho.

QUÉ CAMBIA EN EL ESQUEMA: solo se agrega mensajes_entrevista.usuario_id
(FK nullable a usuarios). El valor nuevo del enum NO necesita cambio de
esquema — se verificó contra la BD que `rol` es varchar(9) sin CHECK
constraint, y 'revisor' mide 7. Igual que pasó con tipo_evento_idea.

POR QUÉ usuario_id Y NO resolverlo al renderizar: el revisor de una idea
puede cambiar por reasignación. Un comentario histórico tiene que seguir
atribuido a quien lo escribió, no a quien tenga la revisión hoy.

BACKFILL: un solo mensaje en esta BD. Se localiza por coincidencia EXACTA de
contenido con una fila de historial_retroalimentacion de la misma idea, que
es como se generan estos mensajes (pedir_cambios escribe el mismo texto en
las dos tablas dentro de la misma transacción). El criterio se aplica en
general, no por id fijo: en otro entorno puede haber otra cantidad.

Se acepta reescribir esta historia —a diferencia de lo que decidimos con los
mensajes degradados— porque acá la corrección es exacta y verificable: no se
adivina nada, se empareja texto idéntico dentro de la misma idea, y el
resultado es que el mensaje queda atribuido a quien realmente lo escribió.
El downgrade lo devuelve a 'asistente' y limpia usuario_id.
"""
from alembic import op
import sqlalchemy as sa

revision = "b8d3f57a2c41"
down_revision = "f2a6d1c73e84"
branch_labels = None
depends_on = None


# Los mensajes de revisor son los que coinciden EXACTO con una
# retroalimentación registrada para la revisión de esa misma idea.
_SELECT_CANDIDATOS = """
    SELECT m.id AS mensaje_id, h.creada_por_id
    FROM mensajes_entrevista m
    JOIN revision_ideas r ON r.idea_id = m.idea_id
    JOIN historial_retroalimentacion h
      ON h.revision_id = r.id AND h.retroalimentacion = m.contenido
    WHERE m.rol = 'asistente'
"""


def upgrade() -> None:
    op.add_column(
        "mensajes_entrevista",
        sa.Column("usuario_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_mensaje_entrevista_usuario",
        "mensajes_entrevista",
        "usuarios",
        ["usuario_id"],
        ["id"],
    )

    conexion = op.get_bind()
    for fila in conexion.execute(sa.text(_SELECT_CANDIDATOS)).fetchall():
        conexion.execute(
            sa.text(
                "UPDATE mensajes_entrevista SET rol = 'revisor', usuario_id = :usuario_id "
                "WHERE id = :mensaje_id"
            ),
            {"usuario_id": fila.creada_por_id, "mensaje_id": fila.mensaje_id},
        )


def downgrade() -> None:
    conexion = op.get_bind()
    conexion.execute(sa.text("UPDATE mensajes_entrevista SET rol = 'asistente' WHERE rol = 'revisor'"))
    op.drop_constraint("fk_mensaje_entrevista_usuario", "mensajes_entrevista", type_="foreignkey")
    op.drop_column("mensajes_entrevista", "usuario_id")
