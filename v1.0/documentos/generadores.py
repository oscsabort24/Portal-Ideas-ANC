"""Generadores de los 6 documentos formales en .docx (python-docx).

Cada función recibe el dict de `datos` ya ensamblado por
documentos/service.py (campos estructurales de la BD + campos
narrativos del stub de IA) y escribe el .docx en `ruta_salida`.

Todo campo usa `.get(clave) or "valor por defecto"` — nunca se escribe
una celda/párrafo vacío en el documento, mismo patrón de fallback
textual que usaba el prototipo v0.1 ("Pendiente de definir", "Por
definir", etc.).

BPMN as-is/to-be se genera como diagrama visual real (cajas y flechas)
con Graphviz — ver _generar_diagrama_bpmn. Requiere el ejecutable
`dot` de Graphviz instalado en el sistema (no solo el paquete de
Python); ver _asegurar_graphviz_disponible para el manejo de ese caso.
"""

import os
import platform
import shutil

import graphviz
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches


def _agregar_encabezado(doc: Document, titulo: str, subtitulo: str) -> None:
    doc.add_heading(titulo, level=0)
    p = doc.add_paragraph(subtitulo)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph()


def _seccion(doc: Document, titulo: str, contenido: str) -> None:
    doc.add_heading(titulo, level=1)
    doc.add_paragraph(contenido or "Pendiente de definir")


def generar_charter_docx(datos: dict, ruta_salida: str) -> None:
    """datos: nombre_proyecto, area_solicitante, solicitante, fecha_emision,
    programa, procedimiento_sig, justificacion_alcance, objetivos,
    beneficios_esperados, principales_entregables,
    riesgos_identificados: list[{riesgo, mitigacion}], estado."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("nombre_proyecto") or "Project Charter", datos.get("programa") or "Transformación Digital")

    tabla_meta = doc.add_table(rows=0, cols=2)
    tabla_meta.style = "Table Grid"
    for etiqueta, clave, default in [
        ("Área Solicitante", "area_solicitante", "No especificada"),
        ("Solicitante", "solicitante", "Participante"),
        ("Fecha de Emisión", "fecha_emision", "—"),
        ("Procedimiento SIG", "procedimiento_sig", "No existe"),
    ]:
        fila = tabla_meta.add_row().cells
        fila[0].text = etiqueta
        fila[1].text = datos.get(clave) or default
    doc.add_paragraph()

    _seccion(doc, "Justificación y Alcance del Proyecto", datos.get("justificacion_alcance"))
    _seccion(doc, "Objetivos del Proyecto", datos.get("objetivos"))
    _seccion(doc, "Beneficios Esperados", datos.get("beneficios_esperados"))
    _seccion(doc, "Principales Entregables", datos.get("principales_entregables"))

    doc.add_heading("Riesgos Identificados", level=1)
    riesgos = datos.get("riesgos_identificados") or []
    if riesgos:
        tabla_riesgos = doc.add_table(rows=1, cols=2)
        tabla_riesgos.style = "Table Grid"
        encabezado = tabla_riesgos.rows[0].cells
        encabezado[0].text = "Riesgo identificado"
        encabezado[1].text = "Estrategia de mitigación"
        for r in riesgos:
            fila = tabla_riesgos.add_row().cells
            fila[0].text = r.get("riesgo") or "Pendiente de definir"
            fila[1].text = r.get("mitigacion") or "Pendiente de definir"
    else:
        doc.add_paragraph("Pendiente de definir")

    doc.add_paragraph()
    doc.add_paragraph(f"Estado del documento: {datos.get('estado') or '—'}")

    doc.save(ruta_salida)


def _asegurar_graphviz_disponible() -> None:
    """Verifica que el ejecutable `dot` de Graphviz esté disponible.

    1. Si ya está en el PATH (cualquier SO), no hace nada.
    2. Si no, intenta agregar rutas candidatas conocidas SEGÚN EL SISTEMA
       OPERATIVO — hoy solo Windows, porque en Linux/macOS Graphviz
       instalado vía el gestor de paquetes (apt/yum/brew) ya queda en el
       PATH del sistema sin necesitar este workaround.
    3. Si sigue sin encontrarse, lanza un RuntimeError descriptivo (en vez
       del ExecutableNotFound genérico de la librería graphviz) que dice
       exactamente qué falta y cómo resolverlo.
    """
    if shutil.which("dot"):
        return

    rutas_candidatas = {
        "Windows": [r"C:\Program Files\Graphviz\bin"],
    }.get(platform.system(), [])

    for ruta in rutas_candidatas:
        if os.path.isdir(ruta):
            os.environ["PATH"] += os.pathsep + ruta
            if shutil.which("dot"):
                return

    raise RuntimeError(
        "Graphviz (el ejecutable 'dot') no está instalado o no está en el PATH "
        "de este proceso. Instálalo desde https://graphviz.org/download/ "
        "(Windows) o con el gestor de paquetes de tu sistema (ej. "
        "'apt install graphviz' en Linux), y asegúrate de que el directorio "
        "bin quede en el PATH — luego reinicia el servidor para que tome el "
        "PATH actualizado."
    )


_FORMA_POR_TIPO = {
    "inicio": "ellipse",
    "fin": "ellipse",
    "tarea": "box",
    "decision": "diamond",
}


def _generar_diagrama_bpmn(pasos: list[dict], ruta_base_sin_extension: str) -> str | None:
    """Genera un PNG (cajas y flechas) para un proceso as-is o to-be.

    El orden de las cajas es el orden del array `pasos` (por índice) —
    NO el campo "id": el stub de IA hoy ni siquiera lo incluye, y no hay
    garantía de que sea secuencial cuando exista en datos reales.

    Devuelve la ruta del PNG generado, o None si `pasos` viene vacío —
    en ese caso el llamador debe usar el fallback de texto "Pendiente de
    definir", igual que el resto de los campos del documento. Un solo
    paso también es válido: se dibuja un único nodo sin flechas (es
    justamente lo que produce el stub de IA hoy).
    """
    if not pasos:
        return None

    _asegurar_graphviz_disponible()

    grafo = graphviz.Digraph(format="png")
    grafo.attr(rankdir="LR")

    for i, paso in enumerate(pasos):
        actor = paso.get("actor") or "—"
        accion = paso.get("accion") or "Pendiente de definir"
        forma = _FORMA_POR_TIPO.get(paso.get("tipo"), "box")
        grafo.node(f"n{i}", f"{actor}: {accion}", shape=forma)

    for i in range(len(pasos) - 1):
        grafo.edge(f"n{i}", f"n{i + 1}")

    return grafo.render(ruta_base_sin_extension, cleanup=True)


def generar_bpmn_docx(datos: dict, ruta_salida: str) -> None:
    """datos: titulo, descripcion, actores: list[str],
    pasos_as_is / pasos_to_be: list[{actor, accion, tipo}].

    Genera un diagrama real por lado (as-is/to-be) con Graphviz y lo
    inserta como imagen — ver _generar_diagrama_bpmn."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("titulo") or "Diagrama de Proceso", "BPMN")

    doc.add_paragraph(datos.get("descripcion") or "Pendiente de definir")

    doc.add_heading("Participantes del proceso", level=1)
    actores = datos.get("actores") or []
    doc.add_paragraph(", ".join(actores) if actores else "No especificados")

    base_sin_extension = os.path.splitext(ruta_salida)[0]

    def _seccion_proceso(titulo_seccion: str, pasos: list[dict], sufijo: str) -> None:
        doc.add_heading(titulo_seccion, level=1)
        ruta_png = _generar_diagrama_bpmn(pasos, f"{base_sin_extension}_{sufijo}")
        if ruta_png:
            doc.add_picture(ruta_png, width=Inches(6.5))
            os.remove(ruta_png)  # ya insertado en el .docx, no hace falta conservarlo en disco
        else:
            doc.add_paragraph("Pendiente de definir")

    _seccion_proceso("Proceso Actual (AS-IS)", datos.get("pasos_as_is") or [], "as_is")
    doc.add_paragraph()
    _seccion_proceso("Proceso Futuro (TO-BE)", datos.get("pasos_to_be") or [], "to_be")

    doc.save(ruta_salida)


def generar_onepager_docx(datos: dict, ruta_salida: str) -> None:
    """datos: titulo, problema, solucion, beneficios: list[str],
    impacto, esfuerzo, proximo_paso."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("titulo") or "One-Pager", "One-pager")

    _seccion(doc, "El problema", datos.get("problema"))
    _seccion(doc, "La solución", datos.get("solucion"))

    doc.add_heading("Beneficios esperados", level=1)
    beneficios = datos.get("beneficios") or []
    if beneficios:
        for b in beneficios:
            doc.add_paragraph(b, style="List Bullet")
    else:
        doc.add_paragraph("No especificados")

    doc.add_paragraph(f"Impacto: {datos.get('impacto') or 'Por definir'}")
    doc.add_paragraph(f"Esfuerzo: {datos.get('esfuerzo') or 'Por definir'}")

    _seccion(doc, "Próximo paso recomendado", datos.get("proximo_paso"))

    doc.save(ruta_salida)


def generar_raci_docx(datos: dict, ruta_salida: str) -> None:
    """datos: titulo, actividades: list[{actividad, roles: {rol: R|A|C|I}}],
    leyenda: dict[str, str]."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("titulo") or "Matriz RACI", "RACI")

    actividades = datos.get("actividades") or []
    roles = sorted({rol for a in actividades for rol in (a.get("roles") or {}).keys()})

    tabla = doc.add_table(rows=1, cols=1 + len(roles))
    tabla.style = "Table Grid"
    encabezado = tabla.rows[0].cells
    encabezado[0].text = "Actividad"
    for i, rol in enumerate(roles, start=1):
        encabezado[i].text = rol

    for a in actividades:
        fila = tabla.add_row().cells
        fila[0].text = a.get("actividad") or "Pendiente de definir"
        valores_rol = a.get("roles") or {}
        for i, rol in enumerate(roles, start=1):
            fila[i].text = valores_rol.get(rol) or "—"

    doc.add_paragraph()
    doc.add_heading("Leyenda", level=1)
    leyenda = datos.get("leyenda") or {}
    for clave, descripcion in leyenda.items():
        doc.add_paragraph(f"{clave}: {descripcion}", style="List Bullet")

    doc.save(ruta_salida)


def generar_bmc_docx(datos: dict, ruta_salida: str) -> None:
    """datos: titulo + los 9 bloques del Business Model Canvas (texto libre c/u)."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("titulo") or "Business Model Canvas", "BMC")

    bloques = [
        ("Socios Clave", "socios_clave"),
        ("Actividades Clave", "actividades_clave"),
        ("Recursos Clave", "recursos_clave"),
        ("Propuesta de Valor", "propuesta_valor"),
        ("Relaciones con Clientes", "relaciones_clientes"),
        ("Canales", "canales"),
        ("Segmentos de Clientes", "segmentos_clientes"),
        ("Estructura de Costos", "estructura_costos"),
        ("Fuentes de Ingreso", "fuentes_ingreso"),
    ]
    for etiqueta, clave in bloques:
        _seccion(doc, etiqueta, datos.get(clave))

    doc.save(ruta_salida)


def generar_business_case_docx(datos: dict, ruta_salida: str) -> None:
    """datos: titulo, resumen_ejecutivo, problema, solucion_propuesta,
    costo_estimado, beneficio_estimado, roi_estimado, payback_estimado,
    supuestos: list[str], recomendacion: Go|No Go|Pendiente de análisis."""
    doc = Document()
    _agregar_encabezado(doc, datos.get("titulo") or "Business Case", "Business Case")

    _seccion(doc, "Resumen Ejecutivo", datos.get("resumen_ejecutivo"))
    _seccion(doc, "El problema", datos.get("problema"))
    _seccion(doc, "Solución propuesta", datos.get("solucion_propuesta"))

    doc.add_heading("Métricas financieras", level=1)
    tabla = doc.add_table(rows=0, cols=2)
    tabla.style = "Table Grid"
    for etiqueta, clave in [
        ("Costo estimado", "costo_estimado"),
        ("Beneficio estimado", "beneficio_estimado"),
        ("ROI estimado", "roi_estimado"),
        ("Payback estimado", "payback_estimado"),
    ]:
        fila = tabla.add_row().cells
        fila[0].text = etiqueta
        fila[1].text = datos.get(clave) or "Por definir"

    doc.add_heading("Supuestos", level=1)
    supuestos = datos.get("supuestos") or []
    if supuestos:
        for s in supuestos:
            doc.add_paragraph(s, style="List Bullet")
    else:
        doc.add_paragraph("No especificados")

    doc.add_paragraph()
    doc.add_paragraph(f"Recomendación: {datos.get('recomendacion') or 'Pendiente de análisis'}")

    doc.save(ruta_salida)


GENERADORES = {
    "charter": generar_charter_docx,
    "bpmn": generar_bpmn_docx,
    "onepager": generar_onepager_docx,
    "raci": generar_raci_docx,
    "bmc": generar_bmc_docx,
    "business_case": generar_business_case_docx,
}
