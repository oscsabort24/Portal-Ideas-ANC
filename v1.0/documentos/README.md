# documentos

Generación de los 6 tipos de documento formal (Charter, BPMN, One-pager, RACI, BMC, Business Case).

## Pendiente futuro: diagrama BPMN visual

El BPMN as-is/to-be se representa hoy como una tabla (Paso / Actor /
Acción / Tipo) en `documentos/generadores.py:generar_bpmn_docx` — no
como un diagrama visual con swimlanes. Un diagrama real con Graphviz
(o similar) queda pendiente: falta decidir el layout (swimlanes por
actor, iconografía de decisión/inicio/fin) y no está confirmado por
Armando todavía. Cuando se defina, el punto de entrada a cambiar es
esa misma función — el resto del módulo (modelo, servicio, endpoints)
no depende de cómo se renderice el contenido internamente.
