"""Plantillas HTML (Jinja2) de los 6 documentos formales.

Cada plantilla recibe exactamente el mismo dict `datos` que ya se guarda
hoy en DocumentoGenerado.contenido (campos estructurales de
documentos/service.py:_contexto_estructural + campos narrativos de la
IA) — no se cambia esa estructura de datos.

Este HTML se reutiliza para TRES cosas (ver documentos/router.py y
documentos/pdf.py):
  a. GET /documentos/{idea_id}/{tipo}/preview — se devuelve tal cual.
  b. Descarga en PDF — Playwright renderiza este mismo HTML con Chromium
     headless (page.pdf()).
  c. Referencia visual para los generadores .docx (documentos/generadores.py),
     que replican la misma paleta con shading/bordes XML de python-docx —
     no son 1:1 porque el formato .docx no soporta CSS, pero comparten
     colores y estructura de secciones.

Paleta consistente en los 6 documentos (azul/naranja de marca, NO el verde
ad-hoc que tenía el prototipo v0.1): azul #2e5faa, naranja de acento
#E8762C. Pie de página: "Portafolio de Iniciativas · Transformación
Digital · Grupo ANC".
"""

import base64
import os

import graphviz
from jinja2 import Template

from documentos.generadores import _FORMA_POR_TIPO, _asegurar_graphviz_disponible

_RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.jpg")


def _logo_base64() -> str:
    """Lee el logo real de Grupo ANC UNA sola vez (a nivel de módulo, ver
    _LOGO_BASE64 más abajo) y lo devuelve como data URI — mismo criterio
    que el diagrama BPMN: el HTML de /preview y el que usa Playwright para
    PDF deben ser autocontenidos, sin depender de una URL externa a un
    archivo estático."""
    with open(_RUTA_LOGO, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


_LOGO_BASE64 = _logo_base64()

_CSS_BASE = """
  :root {
    --primary: #2e5faa; --primary-faint: #eaf1fb;
    --accent: #E8762C; --accent-faint: #FDF2EA;
    --success: #00713d; --success-bg: #E8F5ED;
    --partial: #B45309; --partial-bg: #FEF3C7;
    --border: #DDD9D3; --border-light: #EDEAE5;
    --text: #22282E; --text-muted: #6B7280;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text); margin: 0; padding: 48px 52px; background: #fff;
  }
  .doc-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 28px; padding-bottom: 24px; border-bottom: 3px solid var(--primary);
  }
  .doc-brand { display: flex; align-items: center; gap: 12px; }
  .doc-brand-logo { height: 44px; width: auto; object-fit: contain; }
  .doc-brand-name { font-size: 14px; font-weight: 700; color: var(--primary); }
  .doc-brand-sub { font-size: 11px; color: var(--text-muted); }
  .doc-title-block { text-align: right; }
  .doc-title { font-size: 22px; font-weight: 800; color: var(--primary); letter-spacing: -.3px; }
  .doc-program-tag {
    font-size: 11px; font-weight: 600; color: var(--accent); background: var(--accent-faint);
    border: 1px solid rgba(232,118,44,.25); padding: 3px 10px; border-radius: 20px;
    display: inline-block; margin-top: 6px;
  }
  .charter-meta {
    display: grid; grid-template-columns: 1fr 1fr;
    border: 1px solid var(--border); border-radius: 10px; overflow: hidden;
    margin-bottom: 28px; font-size: 13.5px;
  }
  .meta-row { display: contents; }
  .meta-label {
    background: var(--primary-faint); color: var(--primary); font-weight: 700;
    font-size: 11px; text-transform: uppercase; letter-spacing: .5px;
    padding: 10px 14px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border);
  }
  .meta-value { padding: 10px 14px; border-bottom: 1px solid var(--border); }
  .meta-row:last-child .meta-label, .meta-row:last-child .meta-value { border-bottom: none; }
  .charter-section { margin-bottom: 24px; }
  .section-title {
    font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .8px;
    color: var(--primary); margin-bottom: 8px; padding-bottom: 6px;
    border-bottom: 2px solid var(--primary-faint); display: flex; align-items: center; gap: 8px;
  }
  .section-title::before {
    content: ''; width: 4px; height: 14px; background: var(--accent);
    border-radius: 2px; display: inline-block;
  }
  .section-content { font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
  .risk-table { width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 4px; }
  .risk-table th {
    background: var(--primary); color: #fff; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .5px; padding: 9px 14px; text-align: left;
  }
  .risk-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); vertical-align: top; line-height: 1.5; }
  .risk-table tr:nth-child(even) td { background: var(--primary-faint); }
  .status-row {
    display: flex; align-items: center; justify-content: flex-end;
    margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--border-light); gap: 12px;
  }
  .status-label { font-size: 12px; color: var(--text-muted); font-weight: 600; }
  .status-badge {
    display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700;
    padding: 7px 16px; border-radius: 20px;
  }
  .status-badge.ready { background: var(--success-bg); color: var(--success); border: 1.5px solid rgba(0,113,61,.25); }
  .status-badge.draft { background: var(--partial-bg); color: var(--partial); border: 1.5px solid rgba(180,83,9,.25); }
  .chips-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip {
    font-size: 12.5px; font-weight: 600; color: var(--primary);
    background: var(--primary-faint); border: 1px solid rgba(46,95,170,.25);
    padding: 5px 12px; border-radius: 20px;
  }
  .chip-verde {
    font-size: 13px; font-weight: 600; color: var(--success);
    background: var(--success-bg); border: 1px solid rgba(0,113,61,.25);
    padding: 6px 14px; border-radius: 20px;
  }
  .diagrama-box {
    border: 1px solid var(--border); border-radius: 10px;
    padding: 16px; background: #fafafa; text-align: center;
  }
  .diagrama-box img { max-width: 100%; height: auto; }
  .metricas-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 4px;
  }
  .metrica-box {
    border: 1px solid var(--border); border-radius: 10px; padding: 14px;
    background: var(--primary-faint);
  }
  .metrica-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px;
    color: var(--primary); margin-bottom: 4px;
  }
  .metrica-valor { font-size: 15px; font-weight: 700; color: var(--text); }
  .doc-footer {
    margin-top: 36px; padding-top: 16px; border-top: 1px solid var(--border-light);
    font-size: 11px; color: var(--text-muted); text-align: center; letter-spacing: .4px;
  }
  .bmc-canvas {
    border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-top: 4px;
  }
  .bmc-row { display: grid; }
  .bmc-row-top { grid-template-columns: repeat(5, 1fr); }
  .bmc-row-bottom { grid-template-columns: repeat(2, 1fr); border-top: 1px solid var(--border); }
  .bmc-cell, .bmc-cell-stack { padding: 14px; border-right: 1px solid var(--border-light); }
  .bmc-row-top .bmc-cell:last-child, .bmc-row-top .bmc-cell-stack:last-child { border-right: none; }
  .bmc-row-bottom .bmc-cell:last-child { border-right: none; }
  .bmc-cell-stack { display: flex; flex-direction: column; padding: 0; }
  .bmc-subcell { padding: 14px; flex: 1; }
  .bmc-subcell + .bmc-subcell { border-top: 1px solid var(--border-light); }
  .bmc-title {
    font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .5px;
    color: var(--primary); margin-bottom: 6px;
  }
  .bmc-content { font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; }
"""

_DOC_HEADER = """
  <div class="doc-header">
    <div class="doc-brand">
      <img class="doc-brand-logo" src="data:image/jpeg;base64,%(logo)s" alt="Grupo ANC">
      <div>
        <div class="doc-brand-name">Grupo ANC</div>
        <div class="doc-brand-sub">Alamo · Enterprise · National</div>
      </div>
    </div>
    <div class="doc-title-block">
      <div class="doc-title">{{ nombre_proyecto or titulo or "%(default_title)s" }}</div>
      <div class="doc-program-tag">%(tag)s</div>
    </div>
  </div>
"""

_DOC_FOOTER = """
  <div class="doc-footer">Portafolio de Iniciativas · Transformación Digital · Grupo ANC</div>
"""


def _envolver(titulo_defecto: str, tag: str, cuerpo: str) -> str:
    header = _DOC_HEADER % {"default_title": titulo_defecto, "tag": tag, "logo": _LOGO_BASE64}
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>{_CSS_BASE}</style>
</head>
<body>
{header}
{cuerpo}
{_DOC_FOOTER}
</body>
</html>"""


CHARTER_HTML = _envolver(
    "Project Charter",
    "{{ programa or 'Transformación Digital' }}",
    """
  <div class="charter-meta">
    <div class="meta-row"><div class="meta-label">Nombre del Proyecto</div><div class="meta-value">{{ nombre_proyecto or "—" }}</div></div>
    <div class="meta-row"><div class="meta-label">Área Solicitante</div><div class="meta-value">{{ area_solicitante or "—" }}</div></div>
    <div class="meta-row"><div class="meta-label">Solicitante</div><div class="meta-value">{{ solicitante or "—" }}</div></div>
    <div class="meta-row"><div class="meta-label">Fecha de Emisión</div><div class="meta-value">{{ fecha_emision or "—" }}</div></div>
    <div class="meta-row"><div class="meta-label">Procedimiento SIG</div><div class="meta-value">{{ procedimiento_sig or "No existe" }}</div></div>
  </div>

  <div class="charter-section">
    <div class="section-title">Justificación y Alcance del Proyecto</div>
    <div class="section-content">{{ justificacion_alcance or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Objetivos del Proyecto</div>
    <div class="section-content">{{ objetivos or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Beneficios Esperados</div>
    <div class="section-content">{{ beneficios_esperados or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Principales Entregables</div>
    <div class="section-content">{{ principales_entregables or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Riesgos Identificados</div>
    {% if riesgos_identificados %}
    <table class="risk-table">
      <thead><tr><th>Riesgo identificado</th><th>Estrategia de mitigación</th></tr></thead>
      <tbody>
        {% for r in riesgos_identificados %}
        <tr><td>{{ r.riesgo }}</td><td>{{ r.mitigacion }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="section-content">Pendiente de definir</p>
    {% endif %}
  </div>

  <div class="status-row">
    <span class="status-label">Estado del documento:</span>
    <span class="status-badge {{ 'ready' if 'listo' in (estado or '').lower() else 'draft' }}">{{ estado or "—" }}</span>
  </div>
""",
)


BPMN_HTML = _envolver(
    "Diagrama de Proceso",
    "BPMN",
    """
  <div class="charter-section">
    <div class="section-title">Descripción</div>
    <div class="section-content">{{ descripcion or "Pendiente de definir" }}</div>
  </div>

  <div class="charter-section">
    <div class="section-title">Participantes del proceso</div>
    {% if actores %}
    <div class="chips-row">
      {% for actor in actores %}<span class="chip">{{ actor }}</span>{% endfor %}
    </div>
    {% else %}
    <div class="section-content">No especificados</div>
    {% endif %}
  </div>

  <div class="charter-section">
    <div class="section-title">Proceso Actual (AS-IS)</div>
    {% if diagrama_as_is_base64 %}
    <div class="diagrama-box">
      <img src="data:image/png;base64,{{ diagrama_as_is_base64 }}" alt="Diagrama AS-IS">
    </div>
    {% else %}
    <div class="section-content">Pendiente de definir</div>
    {% endif %}
  </div>

  <div class="charter-section">
    <div class="section-title">Proceso Futuro (TO-BE)</div>
    {% if diagrama_to_be_base64 %}
    <div class="diagrama-box">
      <img src="data:image/png;base64,{{ diagrama_to_be_base64 }}" alt="Diagrama TO-BE">
    </div>
    {% else %}
    <div class="section-content">Pendiente de definir</div>
    {% endif %}
  </div>
""",
)


ONEPAGER_HTML = _envolver(
    "One-Pager",
    "One-pager",
    """
  <div class="charter-section">
    <div class="section-title">El problema</div>
    <div class="section-content">{{ problema or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">La solución</div>
    <div class="section-content">{{ solucion or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Beneficios esperados</div>
    {% if beneficios %}
    <div class="chips-row">
      {% for b in beneficios %}<span class="chip-verde">{{ b }}</span>{% endfor %}
    </div>
    {% else %}
    <div class="section-content">No especificados</div>
    {% endif %}
  </div>
  <div class="charter-section">
    <div class="section-title">Impacto y esfuerzo</div>
    <div class="metricas-grid">
      <div class="metrica-box"><div class="metrica-label">Impacto</div><div class="metrica-valor">{{ impacto or "Por definir" }}</div></div>
      <div class="metrica-box"><div class="metrica-label">Esfuerzo</div><div class="metrica-valor">{{ esfuerzo or "Por definir" }}</div></div>
    </div>
  </div>
  <div class="charter-section">
    <div class="section-title">Próximo paso recomendado</div>
    <div class="section-content">{{ proximo_paso or "Pendiente de definir" }}</div>
  </div>
""",
)


_RACI_COLORES = {
    "R": ("#e8f4fd", "#2e5faa"),
    "A": ("#E8F5ED", "#00713d"),
    "C": ("#FEF3C7", "#B45309"),
    "I": ("#F0F0EF", "#6B7280"),
}

RACI_HTML = _envolver(
    "Matriz RACI",
    "RACI",
    """
  <div class="charter-section">
    <div class="section-title">Actividades y responsables</div>
    {% if actividades %}
    <table class="risk-table">
      <thead>
        <tr>
          <th>Actividad</th>
          {% for rol in roles %}<th>{{ rol }}</th>{% endfor %}
        </tr>
      </thead>
      <tbody>
        {% for a in actividades %}
        <tr>
          <td>{{ a.actividad or "Pendiente de definir" }}</td>
          {% for rol in roles %}
          {% set valor = (a.roles or {}).get(rol) %}
          <td>
            {% if valor %}
            <span class="raci-badge raci-{{ valor }}">{{ valor }}</span>
            {% else %}—{% endif %}
          </td>
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="section-content">Pendiente de definir</p>
    {% endif %}
  </div>

  <div class="charter-section">
    <div class="section-title">Leyenda</div>
    {% if leyenda %}
    <div class="chips-row">
      {% for clave, descripcion in leyenda.items() %}
      <span class="raci-badge raci-{{ clave }}" style="margin-right:4px">{{ clave }}</span>
      <span class="chip" style="margin-right:12px">{{ descripcion }}</span>
      {% endfor %}
    </div>
    {% else %}
    <div class="section-content">No especificada</div>
    {% endif %}
  </div>
""",
).replace(
    "</style>",
    "".join(
        f".raci-{letra} {{ display:inline-flex; align-items:center; justify-content:center; "
        f"width:26px; height:26px; border-radius:6px; font-weight:800; font-size:13px; "
        f"background:{bg}; color:{fg}; }}\n"
        for letra, (bg, fg) in _RACI_COLORES.items()
    )
    + "</style>",
)


BMC_HTML = _envolver(
    "Business Model Canvas",
    "BMC",
    """
  <div class="bmc-canvas">
    <div class="bmc-row bmc-row-top">
      <div class="bmc-cell">
        <div class="bmc-title">Socios Clave</div>
        <div class="bmc-content">{{ bloques.get("socios_clave") or "Pendiente de definir" }}</div>
      </div>
      <div class="bmc-cell-stack">
        <div class="bmc-subcell">
          <div class="bmc-title">Actividades Clave</div>
          <div class="bmc-content">{{ bloques.get("actividades_clave") or "Pendiente de definir" }}</div>
        </div>
        <div class="bmc-subcell">
          <div class="bmc-title">Recursos Clave</div>
          <div class="bmc-content">{{ bloques.get("recursos_clave") or "Pendiente de definir" }}</div>
        </div>
      </div>
      <div class="bmc-cell">
        <div class="bmc-title">Propuesta de Valor</div>
        <div class="bmc-content">{{ bloques.get("propuesta_valor") or "Pendiente de definir" }}</div>
      </div>
      <div class="bmc-cell-stack">
        <div class="bmc-subcell">
          <div class="bmc-title">Relaciones con Clientes</div>
          <div class="bmc-content">{{ bloques.get("relaciones_clientes") or "Pendiente de definir" }}</div>
        </div>
        <div class="bmc-subcell">
          <div class="bmc-title">Canales</div>
          <div class="bmc-content">{{ bloques.get("canales") or "Pendiente de definir" }}</div>
        </div>
      </div>
      <div class="bmc-cell">
        <div class="bmc-title">Segmentos de Clientes</div>
        <div class="bmc-content">{{ bloques.get("segmentos_clientes") or "Pendiente de definir" }}</div>
      </div>
    </div>
    <div class="bmc-row bmc-row-bottom">
      <div class="bmc-cell">
        <div class="bmc-title">Estructura de Costos</div>
        <div class="bmc-content">{{ bloques.get("estructura_costos") or "Pendiente de definir" }}</div>
      </div>
      <div class="bmc-cell">
        <div class="bmc-title">Fuentes de Ingreso</div>
        <div class="bmc-content">{{ bloques.get("fuentes_ingreso") or "Pendiente de definir" }}</div>
      </div>
    </div>
  </div>
""",
)


BUSINESS_CASE_HTML = _envolver(
    "Business Case",
    "Business Case",
    """
  <div class="charter-section">
    <div class="section-title">Resumen Ejecutivo</div>
    <div class="section-content">{{ resumen_ejecutivo or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">El problema</div>
    <div class="section-content">{{ problema or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Solución propuesta</div>
    <div class="section-content">{{ solucion_propuesta or "Pendiente de definir" }}</div>
  </div>
  <div class="charter-section">
    <div class="section-title">Métricas financieras</div>
    <div class="metricas-grid">
      <div class="metrica-box"><div class="metrica-label">Costo estimado</div><div class="metrica-valor">{{ costo_estimado or "Por definir" }}</div></div>
      <div class="metrica-box"><div class="metrica-label">Beneficio estimado</div><div class="metrica-valor">{{ beneficio_estimado or "Por definir" }}</div></div>
      <div class="metrica-box"><div class="metrica-label">ROI estimado</div><div class="metrica-valor">{{ roi_estimado or "Por definir" }}</div></div>
      <div class="metrica-box"><div class="metrica-label">Payback estimado</div><div class="metrica-valor">{{ payback_estimado or "Por definir" }}</div></div>
    </div>
  </div>
  <div class="charter-section">
    <div class="section-title">Supuestos</div>
    {% if supuestos %}
    <div class="chips-row">
      {% for s in supuestos %}<span class="chip">{{ s }}</span>{% endfor %}
    </div>
    {% else %}
    <div class="section-content">No especificados</div>
    {% endif %}
  </div>

  <div class="status-row">
    <span class="status-label">Recomendación:</span>
    <span class="status-badge {{ 'ready' if (recomendacion or '').lower().startswith('go') and not (recomendacion or '').lower().startswith('no go') else 'draft' }}">{{ recomendacion or "Pendiente de análisis" }}</span>
  </div>
""",
)


_TEMPLATES = {
    "charter": CHARTER_HTML,
    "bpmn": BPMN_HTML,
    "onepager": ONEPAGER_HTML,
    "raci": RACI_HTML,
    "bmc": BMC_HTML,
    "business_case": BUSINESS_CASE_HTML,
}


def _diagrama_bpmn_base64(pasos: list[dict]) -> str | None:
    """Igual que generadores.py:_generar_diagrama_bpmn, pero devuelve el
    PNG como base64 en memoria (sin escribir a disco) para embeberlo
    directamente en el HTML como data URI — usado tanto por /preview
    como por la generación de PDF, ninguno de los dos debe depender de
    un archivo intermedio ni de una URL estática."""
    if not pasos:
        return None

    _asegurar_graphviz_disponible()

    grafo = graphviz.Digraph(format="png")
    # rankdir="TB" (vertical): con "LR" el diagrama crecía casi solo en
    # ancho (tira horizontal aplastada e ilegible) — mismo fix aplicado en
    # generadores.py:_generar_diagrama_bpmn, confirmado con el PNG real.
    grafo.attr(rankdir="TB", bgcolor="transparent")
    grafo.attr("node", fontname="Helvetica", fontsize="11")
    grafo.attr("edge", color="#2e5faa")

    for i, paso in enumerate(pasos):
        actor = paso.get("actor") or "—"
        accion = paso.get("accion") or "Pendiente de definir"
        forma = _FORMA_POR_TIPO.get(paso.get("tipo"), "box")
        if paso.get("usado_en_to_be", True):
            estilo = {"style": "filled", "fillcolor": "#eaf1fb", "color": "#2e5faa", "fontcolor": "#22282E"}
        else:
            # Paso del AS-IS que el rediseño TO-BE elimina: gris apagado y
            # borde punteado para distinguirlo de un paso normal.
            estilo = {"style": "filled,dashed", "fillcolor": "#F0F0EF", "color": "#6B7280", "fontcolor": "#6B7280"}
        grafo.node(f"n{i}", f"{actor}\n{accion}", shape=forma, **estilo)

    for i in range(len(pasos) - 1):
        grafo.edge(f"n{i}", f"n{i + 1}")

    png_bytes = grafo.pipe()
    return base64.b64encode(png_bytes).decode("ascii")


def renderizar_documento(tipo: str, datos: dict) -> str:
    """Arma el contexto de cada tipo (incluye cálculos derivados que NO
    viven en `datos` tal cual, como los diagramas BPMN en base64 o la
    lista de roles únicos del RACI) y renderiza la plantilla Jinja2
    correspondiente."""
    template = _TEMPLATES[tipo]
    contexto = dict(datos)

    if tipo == "bpmn":
        contexto["diagrama_as_is_base64"] = _diagrama_bpmn_base64(datos.get("pasos_as_is") or [])
        contexto["diagrama_to_be_base64"] = _diagrama_bpmn_base64(datos.get("pasos_to_be") or [])
    elif tipo == "raci":
        actividades = datos.get("actividades") or []
        contexto["roles"] = sorted({rol for a in actividades for rol in (a.get("roles") or {}).keys()})
    elif tipo == "bmc":
        # Los 9 bloques del canvas viven como campos sueltos en `datos`
        # (segmentos_clientes, propuesta_valor, etc.) — se agrupan aquí
        # en un dict para poder iterarlos con un solo bucle en el template.
        contexto["bloques"] = datos

    # autoescape=True: el contexto trae contenido narrativo generado por la IA
    # a partir de lo que escribió la persona en la entrevista. Con el default
    # de Jinja2 (autoescape=False) ese texto se interpreta como HTML, y el
    # resultado se sirve en un <iframe srcDoc> (VistaPreviaDocumento.tsx) que
    # hereda el origen de la app — un <script> ahí accedería al DOM y al
    # localStorage donde MSAL guarda los tokens. Y los documentos los abren
    # revisores y CAB, no solo el autor: es XSS almacenado contra usuarios de
    # más privilegio.
    #
    # No hace falta ningún |safe: ningún campo depende de que el HTML NO se
    # escape. Los saltos de línea del texto largo se resuelven por CSS
    # (`white-space: pre-wrap`, ver .section-content y .bmc-content), no con
    # <br>; el contexto nunca se arma concatenando tags; y los diagramas van
    # en base64, cuyo alfabeto no contiene ningún carácter que Jinja escape.
    # Verificado renderizando los 26 documentos reales de la BD con y sin
    # autoescape: salida byte a byte idéntica.
    return Template(template, autoescape=True).render(**contexto)
