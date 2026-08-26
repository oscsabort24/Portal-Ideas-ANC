"""marcar mensajes de entrevista degradados

Revision ID: c4a1f8b3d920
Revises: d5e8f21a9c36
Create Date: 2026-08-25

Columna `degradado` en mensajes_entrevista: marca los turnos del asistente
que NO son contenido real de la IA sino texto que generó el backend cuando
la llamada falló (error de API, JSON inválido, mensaje vacío).

Sin esta marca esos mensajes se reinyectaban como contexto en los 7 flujos
que le mandan el historial al modelo — entrevista, análisis de riesgo,
resumen para revisores, preguntas del revisor/CAB, clasificación, asignación
de revisor y generación de los 6 documentos formales. O sea que un fallo
técnico terminaba dentro de entregables que lee el CAB.

BACKFILL POR CONTENIDO: los textos van hardcodeados acá, NO importados de
core.claude_client, a propósito. Una migración es el registro de lo que se
hizo en un momento dado; si mañana alguien cambia una de esas constantes,
esta migración tiene que seguir describiendo lo que efectivamente hizo
cuando corrió, no cambiar de significado retroactivamente.

El backfill es COMPLETO, no aproximado: se verificó en el historial de git
que ninguno de los tres textos tuvo nunca otra redacción (556032f los
introdujo, 1bc30ed/3227233 para el tercero, siempre con el mismo string),
así que no existe ningún mensaje degradado histórico con un texto distinto
al de esta lista.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4a1f8b3d920"
down_revision = "d5e8f21a9c36"
branch_labels = None
depends_on = None

# Copias literales de _RESPUESTA_DEGRADADA_API, _RESPUESTA_DEGRADADA_SIN_PARSEAR
# y _RESPUESTA_REPREGUNTA (core/claude_client.py) al 2026-08-25. Ver el
# docstring: no se importan a propósito.
TEXTOS_DEGRADADOS = (
    "Hubo un problema técnico al procesar tu respuesta. Intenta de nuevo en un momento.",
    "No se pudo procesar la respuesta de la IA. Intenta de nuevo.",
    "Perdón, se me fue la idea. ¿Me lo repetís?",
)


def upgrade() -> None:
    # server_default="0" hace que las filas existentes queden en False sin
    # reescribir la tabla; es NOT NULL para no tener un tercer estado NULL
    # que signifique "no sé".
    op.add_column(
        "mensajes_entrevista",
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Se limita a rol='asistente': el backend nunca genera estos textos como
    # mensaje de usuario, y así un usuario que escriba literalmente una de
    # estas frases no queda marcado por accidente.
    conexion = op.get_bind()
    for texto in TEXTOS_DEGRADADOS:
        conexion.execute(
            sa.text(
                "UPDATE mensajes_entrevista SET degradado = 1 "
                "WHERE rol = 'asistente' AND contenido = :texto"
            ),
            {"texto": texto},
        )


def downgrade() -> None:
    # SQL Server materializa el server_default como un DEFAULT constraint con
    # nombre autogenerado (ej. DF__mensajes___degra__4D5F7D71), y DROP COLUMN
    # falla con el error 5074 mientras ese objeto dependa de la columna. El
    # nombre lo genera el motor y cambia entre bases, así que hay que
    # resolverlo en tiempo de ejecución en vez de hardcodearlo.
    conexion = op.get_bind()
    nombre_constraint = conexion.execute(
        sa.text(
            "SELECT dc.name FROM sys.default_constraints dc "
            "JOIN sys.columns c ON c.default_object_id = dc.object_id "
            "WHERE dc.parent_object_id = OBJECT_ID('mensajes_entrevista') "
            "AND c.name = 'degradado'"
        )
    ).scalar()
    if nombre_constraint:
        # Interpolación en vez de bind: un nombre de objeto no puede ir
        # parametrizado en DDL. El valor sale de sys.default_constraints —
        # metadata del propio motor, nunca entrada externa.
        conexion.execute(sa.text(f"ALTER TABLE mensajes_entrevista DROP CONSTRAINT [{nombre_constraint}]"))

    op.drop_column("mensajes_entrevista", "degradado")
