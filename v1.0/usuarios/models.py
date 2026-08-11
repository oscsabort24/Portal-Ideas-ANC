import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Unicode, UniqueConstraint
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
    """

    __tablename__ = "miembros_cab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    tipo_cab: Mapped[TipoCAB] = mapped_column(Enum(TipoCAB, name="tipo_cab"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="membresias_cab")
