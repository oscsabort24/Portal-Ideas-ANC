"""un departamento pertenece a un solo Portfolio Owner

Revision ID: f2a6d1c73e84
Revises: c4a1f8b3d920
Create Date: 2026-08-26

Regla de negocio: un departamento puede estar asignado a UN solo Portfolio
Owner a la vez. La relación inversa sigue siendo libre — una persona puede
tener varios departamentos.

miembros_cab_departamentos ya tenía uq_miembro_cab_departamento sobre el PAR
(miembro_cab_id, departamento_id), que impide asignar dos veces el MISMO
departamento a la MISMA persona pero no impide asignárselo a dos personas
distintas — justo el caso que la regla prohíbe. Este índice es sobre
departamento_id solo.

POR QUÉ EN LA BD Y NO SOLO EN EL ENDPOINT: una violación de esta regla no
produce un error visible, produce dos personas resolviendo la misma cola de
ideas en paralelo, en silencio. Además, sin restricción en la BD dos altas
concurrentes con el mismo departamento pasan las dos la validación de
aplicación y las dos insertan. La validación del endpoint se mantiene igual
(devuelve 409 con el nombre del dueño actual); esto es la red que la
respalda, no su reemplazo.

NO cubre — a propósito — el caso comodín: un Portfolio Owner sin ninguna
fila acá ve TODOS los departamentos (comites/service.py:departamentos_visibles),
incluidos los que ya tienen dueño. Decisión de negocio confirmada: la
exclusividad es sobre la PROPIEDAD de un departamento (esta fila), no sobre
la visibilidad. Un admin ya ve todo sin ser dueño de nada y eso nunca se
consideró un conflicto; el comodín es el mismo caso por fallback.

ANTES DE APLICAR se auditó la BD: el departamento 1 tenía 3 filas (miembros
de prueba "CAB Prueba/A/B Temporal", ids 1002/1003/1004 de esta tabla) que
se borraron a mano. Si esta migración falla al crear el índice en otro
entorno, es porque ahí también hay duplicados: correr primero

    SELECT departamento_id, COUNT(*) FROM miembros_cab_departamentos
    GROUP BY departamento_id HAVING COUNT(*) > 1

y resolver a quién le queda cada departamento antes de reintentar. No se
automatiza esa limpieza acá: elegir cuál de los dueños duplicados sobrevive
es una decisión de negocio, no algo que una migración pueda adivinar.
"""
from alembic import op

revision = "f2a6d1c73e84"
down_revision = "c4a1f8b3d920"
branch_labels = None
depends_on = None

NOMBRE_INDICE = "uq_departamento_un_solo_portfolio_owner"


def upgrade() -> None:
    op.create_index(
        NOMBRE_INDICE,
        "miembros_cab_departamentos",
        ["departamento_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(NOMBRE_INDICE, table_name="miembros_cab_departamentos")
