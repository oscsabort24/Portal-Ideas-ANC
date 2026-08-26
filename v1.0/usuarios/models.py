import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class RolUsuario(str, enum.Enum):
    colaborador = "colaborador"
    encargado_area = "encargado_area"
    gerente = "gerente"
    admin = "admin"


class TipoCAB(str, enum.Enum):
    innovacion = "innovacion"
    transformacion_digital = "transformacion_digital"


class PaisUsuario(str, enum.Enum):
    CR = "CR"
    GT = "GT"
    NI = "NI"
    PE = "PE"


class CompaniaUsuario(str, enum.Enum):
    ANC_CAR = "ANC_CAR"
    RENTING = "RENTING"
    RENTAS_INT = "RENTAS_INT"


class Departamento(Base):
    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Unicode(150), unique=True, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="departamento")
    puestos: Mapped[list["Puesto"]] = relationship(back_populates="departamento")


class Puesto(Base):
    """Catálogo de puestos, agrupados por departamento.

    El mismo nombre de puesto puede repetirse en departamentos distintos
    (ej. "Facturador" existe en Operaciones y en Renting) — son puestos
    distintos que comparten nombre, no duplicados. La unicidad real es
    por el par (nombre, departamento).
    """

    __tablename__ = "puestos"
    __table_args__ = (UniqueConstraint("nombre", "departamento_id", name="uq_puesto_nombre_departamento"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"), nullable=False)
    es_unico_por_pais: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    departamento: Mapped["Departamento"] = relationship(back_populates="puestos")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="puesto")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    correo: Mapped[str] = mapped_column(Unicode(200), unique=True, nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, name="rol_usuario"), default=RolUsuario.colaborador, nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pais: Mapped[PaisUsuario] = mapped_column(Enum(PaisUsuario, name="pais_usuario"), nullable=False)
    compania: Mapped[CompaniaUsuario] = mapped_column(
        Enum(CompaniaUsuario, name="compania_usuario"), nullable=False
    )

    departamento_id: Mapped[int | None] = mapped_column(ForeignKey("departamentos.id"))
    departamento: Mapped["Departamento | None"] = relationship(back_populates="usuarios")

    puesto_id: Mapped[int | None] = mapped_column(ForeignKey("puestos.id"), nullable=True)
    puesto: Mapped["Puesto | None"] = relationship(back_populates="usuarios")

    reporta_a_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    reporta_a: Mapped["Usuario | None"] = relationship(remote_side=[id])

    membresias_cab: Mapped[list["MiembroCAB"]] = relationship(back_populates="usuario")


class MiembroCAB(Base):
    """Pertenencia de un usuario a un comité (CAB Innovación o CAB TD).

    Separado de Usuario porque ser miembro de un CAB es independiente
    del rol/jerarquía del usuario en el organigrama.

    `tipo_cab` es metadata pura desde CAB-por-departamento — ya NO es el
    criterio de acceso (eso lo determina `departamentos` vía
    MiembroCABDepartamento, ver comites/service.py:_departamentos_visibles).
    """

    __tablename__ = "miembros_cab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    tipo_cab: Mapped[TipoCAB] = mapped_column(Enum(TipoCAB, name="tipo_cab"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="membresias_cab")
    departamentos_asignados: Mapped[list["MiembroCABDepartamento"]] = relationship(
        back_populates="miembro_cab", cascade="all, delete-orphan"
    )

    @property
    def departamentos(self) -> list["Departamento"]:
        """Para serializar directo en MiembroCABDetalleOut.departamentos
        (lista de Departamento, no de filas de la tabla puente)."""
        return [d.departamento for d in self.departamentos_asignados]


class MiembroCABDepartamento(Base):
    """Un departamento que un miembro de CAB puede ver/atender (N:M).

    Ausencia de TODA fila para un MiembroCAB se interpreta como "ve todos
    los departamentos" — ver comites/service.py:_departamentos_visibles.
    """

    __tablename__ = "miembros_cab_departamentos"
    __table_args__ = (
        UniqueConstraint("miembro_cab_id", "departamento_id", name="uq_miembro_cab_departamento"),
        # Un departamento pertenece a UN solo Portfolio Owner (la inversa sigue
        # libre: una persona puede tener varios departamentos). El unique de
        # arriba es sobre el PAR y no cubre esto — impide repetir el mismo
        # departamento en la misma persona, no asignárselo a dos personas.
        # Ver alembic/versions/f2a6d1c73e84_*.
        Index("uq_departamento_un_solo_portfolio_owner", "departamento_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    miembro_cab_id: Mapped[int] = mapped_column(ForeignKey("miembros_cab.id"), nullable=False)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"), nullable=False)

    miembro_cab: Mapped["MiembroCAB"] = relationship(back_populates="departamentos_asignados")
    departamento: Mapped["Departamento"] = relationship()


class ResponsableArea(Base):
    """Mapeo determinístico área -> persona responsable de revisar.

    Tabla lista para Fase 3, pero TODAVÍA NO ACTIVADA en el código —
    revision/service.py:_buscar_encargado_activo sigue resolviendo por
    departamento+rol directamente, no por esta tabla, mientras no exista
    el seed con los datos reales del negocio (nace vacía a propósito).
    """

    __tablename__ = "responsables_area"
    __table_args__ = (
        UniqueConstraint(
            "departamento_id", "pais", "compania", "prioridad",
            name="uq_responsable_area_depto_pais_compania_prioridad",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False)
    pais: Mapped["PaisUsuario | None"] = mapped_column(
        Enum(PaisUsuario, name="pais_responsable_area"), nullable=True
    )
    compania: Mapped["CompaniaUsuario | None"] = mapped_column(
        Enum(CompaniaUsuario, name="compania_responsable_area"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vigente_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vigente_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    departamento: Mapped["Departamento"] = relationship()
    usuario: Mapped["Usuario"] = relationship()
