# documentos

Generación de los 6 tipos de documento formal (Charter, BPMN, One-pager, RACI, BMC, Business Case).

## Diagrama BPMN visual (Graphviz)

El BPMN as-is/to-be se genera como un diagrama real (cajas y flechas)
con Graphviz — ver `documentos/generadores.py:_generar_diagrama_bpmn` y
`generar_bpmn_docx`. Se generan 2 imágenes separadas (as-is / to-be),
insertadas como PNG en el mismo `.docx`; los archivos PNG temporales se
borran del disco después de insertarlos (ya quedan copiados dentro del
`.docx`).

Formas por tipo de paso: `inicio`/`fin` → óvalo, `tarea` → rectángulo,
`decision` → rombo. El orden de las cajas es el orden del array (por
índice), no el campo `"id"` — el stub de IA hoy ni siquiera lo incluye.

**Requiere el ejecutable `dot` de Graphviz instalado en el sistema**,
no solo el paquete de Python (`pip install graphviz` es solo un
wrapper que invoca `dot` por subprocess). Ver
https://graphviz.org/download/ para Windows, o el gestor de paquetes
de tu distro en Linux/macOS (ej. `apt install graphviz`) — en Linux
normalmente ya queda en el PATH del sistema sin pasos adicionales.

Si `dot` no está en el PATH del proceso, `_asegurar_graphviz_disponible`
intenta agregar rutas candidatas conocidas según el sistema operativo
(hoy solo Windows: `C:\Program Files\Graphviz\bin`) antes de fallar con
un error descriptivo. Nota de esta sesión: si actualizás la variable de
entorno PATH del sistema, un proceso de `uvicorn` ya en ejecución **no
la hereda automáticamente** — hay que reiniciarlo.
