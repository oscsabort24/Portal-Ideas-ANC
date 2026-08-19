# Diseño pendiente de aprobación

Estos archivos **no son código activo**. La extensión `.preview` los mantiene
fuera de todo lo que Python importa y de lo que alembic escanea, así que el
backend arranca normalmente con ellos presentes.

## ✅ Fases 3 y 4, y CAB por departamento con reasignación — YA APLICADAS

`alembic current == alembic heads == a3f7c9e21d68`. El código real
(`v1.0/usuarios/models.py`, `v1.0/revision/*`, `v1.0/comites/*`,
`v1.0/ideas/models.py`, `v1.0/core/reasignacion.py`) ya incluye Fase 3,
Fase 4, y CAB por departamento con reasignación — las migraciones
correspondientes (`b4d17c9e5a20`, `c9f3e820d114`, `a3f7c9e21d68`) están
en `v1.0/alembic/versions/`, ya corridas. Las copias `.preview` de acá se
conservan como registro histórico del diseño, no como algo pendiente de
aplicar.

**Desviación deliberada de Fase 3**: la tabla `responsables_area` existe
en la base, pero `revision/service.py:_buscar_encargado_activo` **NO la
usa** — sigue resolviendo por departamento+rol directamente. Se decidió
así porque la tabla nace vacía sin el seed de datos reales del negocio, y
activarla habría roto la asignación automática para todos los usuarios de
prueba. Ver `cab-departamento-reasignacion.md.preview` para el detalle.
Cuando exista ese seed, `_buscar_encargado_activo` es el único punto a
cambiar.

**Rename aplicado**: `revisor_propuesto_id` (nombre original de Fase 4)
se aplicó como `propuesto_a_id`, para que el mismo nombre sirva también
en `comite_ideas` vía el mixin compartido (`core/reasignacion.py`).

## Contenido

| Archivo | Qué es | Estado |
|---|---|---|
| `fase3-4-modelos-router-schemas.diff.preview` | Diseño original de Fases 3 y 4 | Aplicado (con el rename de `propuesto_a_id`, ver arriba) |
| `b4d17c9e5a20_responsables_area_y_origen_asignacion.py.preview` | Migración de Fase 3 | Aplicada — copia real en `v1.0/alembic/versions/` |
| `c9f3e820d114_historial_idea_y_reasignacion_con_aceptacion.py.preview` | Migración de Fase 4 | Aplicada — copia real en `v1.0/alembic/versions/` |
| `cab-departamento-y-criterios-ia.md.preview` | Diseño original de CAB por departamento | Sección 1 superseded por `cab-departamento-reasignacion.md.preview` (aplicado); sección 2 superseded por `cascada-revisor-y-criterios-texto.md.preview` (sin aplicar) |
| `cascada-revisor-y-criterios-texto.md.preview` | Cascada de asignación de revisor (jefe inmediato → CAB del departamento → pendiente_asignacion) y migración de criterios de IA a texto | Sección 2 (criterios en texto) YA APLICADA — ver `9c2f4e71a0b3` abajo. Sección 1 (la cascada en sí) sigue sin aplicar |
| `9c2f4e71a0b3_criterios_ia_texto_y_entrevista.py.preview` | Migración de la tabla `criterios_ia` | Aplicada |
| `fase-permisos-por-rol.md.preview` | Módulo de permisos por rol configurable | Aplicado |
| `4d81f6c93a52_permisos_rol.py.preview` | Migración de `permisos_rol` | Aplicada |
| `cab-departamento-reasignacion.md.preview` | Implementación final de CAB por departamento + reasignación (mixin compartido con `revision/`) | **Aplicado en este commit** |
| `a3f7c9e21d68_cab_por_departamento_y_reasignacion.py.preview` | Migración de `miembros_cab_departamentos` + reasignación en `comite_ideas` | **Aplicada en este commit** — copia real en `v1.0/alembic/versions/` |

## Lo que sigue genuinamente pendiente de diseño/aprobación

- La cascada de asignación de revisor en sí (`cascada-revisor-y-criterios-texto.md.preview`,
  sección 1: jefe inmediato → CAB del departamento → pendiente_asignacion)
  — no se aplicó, sigue siendo diseño.
- Fase 3: ¿el mapeo determinístico (`responsables_area`, todavía inactivo)
  cubre también idea → CAB en `clasificacion/`, o solo el revisor?
- Fase 4: el plazo de expiración quedó en 3 días **hábiles**, sin calendario
  de feriados (no existe en el sistema para los 4 países).
- Fase 4: la notificación es solo badge in-app. `notificaciones/` tiene el
  envío de correo en stub, sin credenciales SMTP.
- El seed real de `responsables_area` con los datos del negocio — sin él,
  Fase 3 sigue siendo esquema inactivo (ver desviación deliberada arriba).
