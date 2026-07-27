"""fix encoding: varchar cp1252 -> nvarchar en columnas de texto libre

Revision ID: 1a2b3c4d5e6f
Revises: 8601a283f177
Create Date: 2026-07-22

CONTEXTO: core/database.py configuraba setdecoding(SQL_CHAR, cp1252) para
poder LEER acentos correctamente desde varchar, pero nunca configuraba
setencoding() para la ESCRITURA — SQLAlchemy bindea columnas String/Text
como parámetros SQL_CHAR, y pyodbc los codificaba con cp1252, causando
UnicodeEncodeError con cualquier carácter fuera de ese charset (ej. "→").
Ver core/database.py para el fix de setencoding() que acompaña esta
migración, y los models.py de cada módulo (String/Text -> Unicode).

Esta migración cambia a NVARCHAR/NVARCHAR(MAX) las columnas de texto
libre (no las de tipo Enum, que son códigos ASCII controlados por la
app — nunca reciben texto generado por IA/usuario, no tienen el bug).

SEGURIDAD DE DATOS: ALTER COLUMN de VARCHAR/TEXT a NVARCHAR/NVARCHAR(MAX)
en SQL Server reinterpreta los bytes existentes usando la collation de
la columna (SQL_Latin1_General_CP1_CI_AS = CP1252) y los re-codifica a
UTF-16 — es una conversión sin pérdida para todo el contenido que hoy
está correctamente en CP1252. La ÚNICA excepción es contenido que ya se
corrompió ANTES de esta migración (ej. el "→" de la idea 22, que hoy ya
está guardado como "?" literal) — ese dato ya se perdió al escribirse y
ningún ALTER COLUMN puede recuperarlo; es un problema de datos
preexistente, no algo que esta migración pueda o deba arreglar.

Para las columnas con UNIQUE constraint (usuarios.correo,
departamentos.nombre), el constraint fue creado sin nombre explícito en
la migración 71b48f37f615 (unique=True inline) — SQL Server le asignó un
nombre autogenerado que no conocemos de antemano. Esta migración lo
busca dinámicamente vía sys.key_constraints antes de hacer DROP, y lo
recrea con un nombre explícito (uq_usuarios_correo / uq_departamentos_nombre)
para que futuras migraciones sean deterministas.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

revision = "1a2b3c4d5e6f"
down_revision = "8601a283f177"
branch_labels = None
depends_on = None


def _nombre_constraint_unico(conn, tabla: str, columna: str) -> str:
    """Busca el nombre real del UNIQUE constraint autogenerado por SQL
    Server sobre una sola columna (creado vía unique=True inline, sin
    nombre explícito, en la migración inicial)."""
    row = conn.execute(
        sa.text(
            """
            SELECT kc.name
            FROM sys.key_constraints kc
            JOIN sys.tables t ON t.object_id = kc.parent_object_id
            JOIN sys.index_columns ic ON ic.object_id = kc.parent_object_id
                AND ic.index_id = kc.unique_index_id
            JOIN sys.columns c ON c.object_id = ic.object_id
                AND c.column_id = ic.column_id
            WHERE t.name = :tabla AND c.name = :columna AND kc.type = 'UQ'
            """
        ),
        {"tabla": tabla, "columna": columna},
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"No se encontró UNIQUE constraint para {tabla}.{columna} — "
            "revisar manualmente antes de continuar."
        )
    return row[0]


def _constraint_existe(conn, nombre: str) -> bool:
    row = conn.execute(
        sa.text("SELECT 1 FROM sys.key_constraints WHERE name = :nombre"),
        {"nombre": nombre},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- columnas con UNIQUE constraint autogenerado: drop -> alter -> recrear con nombre explícito ---
    uq_correo = _nombre_constraint_unico(conn, "usuarios", "correo")
    op.drop_constraint(uq_correo, "usuarios", type_="unique")
    op.alter_column(
        "usuarios", "correo",
        existing_type=sa.String(200),
        type_=sa.Unicode(200),
        existing_nullable=False,
    )
    op.create_unique_constraint("uq_usuarios_correo", "usuarios", ["correo"])

    uq_depto = _nombre_constraint_unico(conn, "departamentos", "nombre")
    op.drop_constraint(uq_depto, "departamentos", type_="unique")
    op.alter_column(
        "departamentos", "nombre",
        existing_type=sa.String(150),
        type_=sa.Unicode(150),
        existing_nullable=False,
    )
    op.create_unique_constraint("uq_departamentos_nombre", "departamentos", ["nombre"])

    # puestos: el constraint compuesto ya tiene nombre explícito en el modelo
    op.drop_constraint("uq_puesto_nombre_departamento", "puestos", type_="unique")
    op.alter_column(
        "puestos", "nombre",
        existing_type=sa.String(200),
        type_=sa.Unicode(200),
        existing_nullable=False,
    )
    op.create_unique_constraint(
        "uq_puesto_nombre_departamento", "puestos", ["nombre", "departamento_id"]
    )

    # --- resto de columnas String -> NVARCHAR(n), sin constraints que estorben ---
    op.alter_column("usuarios", "nombre", existing_type=sa.String(200), type_=sa.Unicode(200), existing_nullable=False)
    op.alter_column("ideas", "titulo", existing_type=sa.String(300), type_=sa.Unicode(300), existing_nullable=False)
    op.alter_column("ideas", "sugerencia_revisor_autor", existing_type=sa.String(300), type_=sa.Unicode(300), existing_nullable=True)
    op.alter_column("rice_evaluaciones", "area", existing_type=sa.String(200), type_=sa.Unicode(200), existing_nullable=False)
    op.alter_column("rice_evaluaciones", "lider_funcional", existing_type=sa.String(200), type_=sa.Unicode(200), existing_nullable=False)
    op.alter_column("documentos_criterio", "nombre_archivo", existing_type=sa.String(300), type_=sa.Unicode(300), existing_nullable=False)
    op.alter_column("documentos_criterio", "ruta_archivo", existing_type=sa.String(500), type_=sa.Unicode(500), existing_nullable=False)
    op.alter_column("documentos_generados", "ruta_archivo", existing_type=sa.String(500), type_=sa.Unicode(500), existing_nullable=False)
    op.alter_column("pines_admin", "pin_hash", existing_type=sa.String(200), type_=sa.Unicode(200), existing_nullable=False)

    # --- columnas Text -> NVARCHAR(MAX) ---
    op.alter_column("ideas", "descripcion", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=True)
    op.alter_column("ideas", "motivo_sugerencia_revisor_autor", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=True)
    op.alter_column("mensajes_entrevista", "contenido", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=False)
    op.alter_column("revision_ideas", "retroalimentacion", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=True)
    op.alter_column("revision_ideas", "justificacion_ia", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=True)
    op.alter_column("historial_retroalimentacion", "retroalimentacion", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=False)
    op.alter_column("comite_ideas", "motivo_rechazo", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=True)
    op.alter_column("analisis_riesgo_ideas", "justificacion", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=False)
    op.alter_column("documentos_generados", "contenido", existing_type=sa.Text(), type_=mssql.NVARCHAR(None), existing_nullable=False)


def downgrade() -> None:
    """ROLLBACK: revierte NVARCHAR -> VARCHAR/TEXT original.

    ADVERTENCIA DE PÉRDIDA DE DATOS: si entre el upgrade y este downgrade
    se insertó contenido con caracteres fuera de CP1252 (ej. "→", emojis,
    comillas tipográficas — exactamente lo que este fix habilita), ese
    contenido se degradará a '?' literal al volver a VARCHAR/TEXT, porque
    CP1252 no puede representarlo. Antes de correr este downgrade en un
    ambiente con datos reales, hacer un respaldo de las tablas afectadas
    (o backup completo de la BD) si existe la posibilidad de que se haya
    escrito contenido no-CP1252 desde el upgrade.

    Nota sobre nombres de constraint: los UNIQUE de usuarios.correo y
    departamentos.nombre originalmente no tenían nombre explícito (SQL
    Server les asignó uno autogenerado que nunca registramos). Este
    downgrade los recrea con nombre explícito "_legacy" — funcionalmente
    idéntico (mismo UNIQUE), pero el nombre del constraint en sys.objects
    quedará distinto al que tenía antes del upgrade original.
    """
    # --- Text -> NVARCHAR(MAX) revertido a TEXT ---
    for tabla, columna, nullable in [
        ("documentos_generados", "contenido", False),
        ("analisis_riesgo_ideas", "justificacion", False),
        ("comite_ideas", "motivo_rechazo", True),
        ("historial_retroalimentacion", "retroalimentacion", False),
        ("revision_ideas", "justificacion_ia", True),
        ("revision_ideas", "retroalimentacion", True),
        ("mensajes_entrevista", "contenido", False),
        ("ideas", "motivo_sugerencia_revisor_autor", True),
        ("ideas", "descripcion", True),
    ]:
        op.alter_column(tabla, columna, existing_type=mssql.NVARCHAR(None), type_=sa.Text(), existing_nullable=nullable)

    # --- String -> NVARCHAR(n) revertido a VARCHAR(n) ---
    for tabla, columna, largo, nullable in [
        ("pines_admin", "pin_hash", 200, False),
        ("documentos_generados", "ruta_archivo", 500, False),
        ("documentos_criterio", "ruta_archivo", 500, False),
        ("documentos_criterio", "nombre_archivo", 300, False),
        ("rice_evaluaciones", "lider_funcional", 200, False),
        ("rice_evaluaciones", "area", 200, False),
        ("ideas", "sugerencia_revisor_autor", 300, True),
        ("ideas", "titulo", 300, False),
        ("usuarios", "nombre", 200, False),
    ]:
        op.alter_column(tabla, columna, existing_type=sa.Unicode(largo), type_=sa.String(largo), existing_nullable=nullable)

    # --- columnas con UNIQUE: drop nombre nuevo -> alter -> recrear con nombre "_legacy" ---
    op.drop_constraint("uq_puesto_nombre_departamento", "puestos", type_="unique")
    op.alter_column("puestos", "nombre", existing_type=sa.Unicode(200), type_=sa.String(200), existing_nullable=False)
    op.create_unique_constraint("uq_puesto_nombre_departamento", "puestos", ["nombre", "departamento_id"])

    op.drop_constraint("uq_departamentos_nombre", "departamentos", type_="unique")
    op.alter_column("departamentos", "nombre", existing_type=sa.Unicode(150), type_=sa.String(150), existing_nullable=False)
    op.create_unique_constraint("uq_departamentos_nombre_legacy", "departamentos", ["nombre"])

    op.drop_constraint("uq_usuarios_correo", "usuarios", type_="unique")
    op.alter_column("usuarios", "correo", existing_type=sa.Unicode(200), type_=sa.String(200), existing_nullable=False)
    op.create_unique_constraint("uq_usuarios_correo_legacy", "usuarios", ["correo"])
