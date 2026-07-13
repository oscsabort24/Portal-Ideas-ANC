"""Script de importación única para poblar Departamento con los departamentos reales de Grupo ANC.

Se corre una vez (o varias — es idempotente: omite los que ya existen por nombre exacto).
No borra ni modifica departamentos de prueba existentes.

Uso: python -m scripts.seed_departamentos
"""

from core.database import SessionLocal
from usuarios.models import Departamento

DEPARTAMENTOS = [
    "Administración",
    "Área Leisure",
    "Bodega",
    "Comercial",
    "Compras",
    "Finanzas",
    "Fleet Management",
    "Flota",
    "Innovación",
    "Mantenimiento",
    "Mercadeo",
    "Operaciones",
    "Renting",
    "Reservas y Servicio al Cliente",
    "Talento Humano",
    "Telematics",
    "Transformación Digital",
    "Venta Vehículos",
]


def main() -> None:
    db = SessionLocal()
    creados = []
    omitidos = []
    try:
        for nombre in DEPARTAMENTOS:
            existe = db.query(Departamento).filter(Departamento.nombre == nombre).first()
            if existe:
                omitidos.append(nombre)
                continue
            db.add(Departamento(nombre=nombre))
            creados.append(nombre)
        db.commit()
    finally:
        db.close()

    print(f"Creados: {len(creados)}")
    for nombre in creados:
        print(f"  + {nombre}")
    print(f"Ya existían (omitidos): {len(omitidos)}")
    for nombre in omitidos:
        print(f"  = {nombre}")


if __name__ == "__main__":
    main()
