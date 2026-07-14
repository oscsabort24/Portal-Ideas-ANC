"""Script de importación única para poblar Puesto con el catálogo real de Grupo ANC.

Se corre una vez (o varias — es idempotente: omite los que ya existen por el
par (nombre, departamento) exacto). Requiere que scripts.seed_departamentos ya
se haya corrido antes (los 18 departamentos deben existir).

Uso: python -m scripts.seed_puestos
"""

from core.database import SessionLocal
from usuarios.models import Departamento, Puesto

PUESTOS_POR_DEPARTAMENTO = {
    "Mantenimiento": [
        "Alistador",
        "Auxiliar de Fuera de Flota y Nuevos",
        "Auxiliar de Talleres Externos",
        "Ayudante de Mecanico (Paises)",
        "Encargado de Torre de Control",
        "Enderezado y Pintura",
        "Gerente Mantenimiento",
        "Jefe de Flota y Mantenimiento",
        "Jefe de Mantenimiento",
        "Jefe de Mantenimiento Ren a Car",
        "Jefe de Mecanicos",
        "Mecanico 1",
        "Mecanico 3",
        "Mecanico Lider",
        "Mecánico 2",
        "Pintor",
        "Tecnico de Experiencia",
    ],
    "Operaciones": [
        "Agente Rentista",
        "Agente Rentista Nocturno",
        "Agente Rentista Sr.",
        "Agente de Retorno",
        "Agente de Salida",
        "Agente de Salida Nocturno",
        "Asesor de Movilidad",
        "Auxiliar de Operaciones",
        "Ayudante de Mecanico",
        "Chofer Lavador Petén",
        "Chofer Microbús",
        "Chofer de Grua (araña)",
        "Chofer lavador",
        "Coordinador de Zona",
        "Ejecutivo (a) de Reservaciones",
        "Ejecutivo de Servicio al Cliente y Reservaciones",
        "Encargado (a) de Daños y Cobros",
        "Facturador",
        "Gerente de Operaciones",
        "Jefe Logística Patio",
        "Jefe Pais",
        "Jefe de Calidad",
        "Jefe de Estacion",
        "Jefe de Experiencia y Contact Center",
        "Jefe de Flota",
        "Jefe de Operaciones",
        "Jefe de calidad Combex",
        "Jefe de calidad Hincapie",
        "Jefe de estación home city",
        "Mecanico",
        "Mecanico 1",
        "Mensajero",
        "Paletero",
        "Parrillero",
        "Parrillero Nocturno",
        "Peletero",
        "Quarterback",
        "Quarterback Nocturno",
        "Supervisor de Aeropuerto",
        "Supervisor de Patio",
        "Supervisor de Retorno",
    ],
    "Finanzas": [
        "Analista Financiera",
        "Analista de Infraestructura",
        "Analista de Nomina",
        "Asistente Administrativo",
        "Asistente administrativo - contable",
        "Asistente de Bodega",
        "Asistente de Contabilidad",
        "Asistente de cuentas por cobrar",
        "Auxiliar Contable",
        "Comprador",
        "Comprador Jr",
        "Contador",
        "Contador Junior",
        "Contador Senior",
        "Contralor de Estaciones",
        "Contralor de Gastos",
        "Encargado (a) de Contabilidad",
        "Encargado (a) de daños y cobros",
        "Gerente Financiero",
        "Gerente Jr. Tesorería",
        "Gerente de Contabilidad",
        "Gestor (a) de Cuentas por Cobrar",
        "Gestor (a) de Cuentas por Pagar",
        "Gestor de Control de Pagos",
        "Gestor de Cuentas por Pagar",
        "Jefe Control Interno",
        "Jefe de Contabilidad",
        "Jefe de Nomina",
        "Jefe de Regional Cuentas por Cobrar",
        "Jefe de TI",
        "Jefe de Tesoreria",
        "Mensajero",
    ],
    "Flota": [
        "Asistente Administrativo de Flota",
        "Asistente Legal",
        "Asistente Operativo de Flota",
        "Chofer Grua Araña",
        "Encargado (a) de Flota",
        "Jefe de Flota",
    ],
    "Administración": [
        "Auxiliar de Compras y Bodega (Paises)",
        "CEO",
        "Conserje",
        "Gerente General de Pais",
        "Gerente de País",
        "Jefe de Compras y Bodega",
        "Secretaria de Gerencia",
    ],
    "Comercial": [
        "Analista de Fleet Management",
        "Asesor de Experiencia",
        "Asesor de Experiencia In House",
        "Asesor de Movilidad",
        "Asesor de Movilidad Leisure/ RINTL",
        "Asesor de Movilidiad venta de vehiculos",
        "Asesor de movilidad Corporativo",
        "Asesor de movilidad carro de trabajo",
        "Asesora de Movilidad",
        "Ejecutivo de Reservas Internacionales",
        "Ejecutivo in House",
        "Encargado (a) de Reservaciones Internacionales",
        "Gerente Comercial",
        "Gerente Comercial Regional",
        "Gerente de Ctas. Corporativas y Agencia",
        "Jefe Comercial",
        "Jefe de Ventas Vehículos de Trabajo",
        "Tecnico de Experiencia",
        "Vendedor de Autos Usados",
    ],
    "Mercadeo": [
        "Analista de Revenue Managment",
        "Coordinador de Contenido",
        "Diseñador Grafico",
        "Estratega Digital",
        "Gerente de Mercadeo",
        "Jefe de Mercadeo",
        "Jefe de Revenue Managment",
        "Revenue Managment Sr",
    ],
    "Compras": [
        "Encargado (a) de Bodega",
        "Jefe de Compras",
    ],
    "Reservas y Servicio al Cliente": [
        "Ejecutivo (a) de Reservaciones",
        "Ejecutivo (a) de Servicio al Cliente",
    ],
    "Venta Vehículos": [
        "Asesor de Movilidad",
        "Asesor de Movilidad B2C",
        "Asistente de Ventas",
        "Gerente Venta de Vehiculos",
        "Jefe de Ventas Vehículos B2C",
    ],
    "Transformación Digital": [
        "Analista de Negocios",
        "Ingeniero de Datos",
        "Jefe de Transformación Digital",
    ],
    "Renting": [
        "Analista de Fleet Management",
        "Asesor de Experiencia In House",
        "Asesor de Fleet Management",
        "Asesor de Movilidad",
        "Asesor de Movilidad B2B",
        "Asesor de Servicio",
        "Asesor de experiencia",
        "Asesor de movilidad Renting",
        "Asistente Administrativo",
        "Asistente Operativo In House",
        "Asistente Operativo Renting",
        "Especialista en Sistemas de Flota",
        "Facturador",
        "Gerente de Renting y Fleet Managment",
        "Jefe Comercial",
        "Jefe Operaciones de Renting y Fleet Management",
        "Jefe comercial Renting",
        "Jefe de Mantenimiento Renting",
        "Jefe de Operaciones Telematics",
        "Jefe de Ventas Renting Fleet Management",
    ],
    "Talento Humano": [
        "Asistente de Talento Humano",
        "Coordinadora de Talento Humano",
        "Encargada de Aprendizaje y Desarrollo",
        "Gerente de Talento Humano",
        "HRBP",
        "Recepcionista",
    ],
    "Área Leisure": [
        "Asesor de Movilidad",
        "Asesor de Movilidad Leisure Francés",
        "Asistente de Ventas",
        "Gerente de Leisure",
    ],
    "Innovación": [
        "Administrador de Proyectos",
        "Gerente Regional Telematics",
        "Investigador de Nuevos Negocios y Estrategia",
        "Jefe de Iniciativas Estratégicas",
    ],
    "Bodega": [
        "Asistente de Bodega",
        "Bodeguero 2",
    ],
    "Telematics": [
        "Instalador Técnico",
    ],
    "Fleet Management": [
        "Analista de Fleet Management",
    ],
}


def main() -> None:
    db = SessionLocal()
    creados = []
    omitidos = []
    sin_departamento = []
    try:
        for nombre_departamento, puestos in PUESTOS_POR_DEPARTAMENTO.items():
            departamento = db.query(Departamento).filter(Departamento.nombre == nombre_departamento).first()
            if not departamento:
                sin_departamento.append(nombre_departamento)
                continue
            for nombre_puesto in puestos:
                existe = (
                    db.query(Puesto)
                    .filter(Puesto.nombre == nombre_puesto, Puesto.departamento_id == departamento.id)
                    .first()
                )
                if existe:
                    omitidos.append(f"{nombre_departamento} / {nombre_puesto}")
                    continue
                db.add(Puesto(nombre=nombre_puesto, departamento_id=departamento.id))
                creados.append(f"{nombre_departamento} / {nombre_puesto}")
        db.commit()
    finally:
        db.close()

    print(f"Creados: {len(creados)}")
    for nombre in creados:
        print(f"  + {nombre}")
    print(f"Ya existían (omitidos): {len(omitidos)}")
    for nombre in omitidos:
        print(f"  = {nombre}")
    if sin_departamento:
        print(f"Departamentos no encontrados en la BD (omitidos por completo): {len(sin_departamento)}")
        for nombre in sin_departamento:
            print(f"  ! {nombre} — corre scripts.seed_departamentos primero")


if __name__ == "__main__":
    main()
