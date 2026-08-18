# Diseño pendiente de aprobación — Fases 3 y 4

Estos archivos **no son código activo**. La extensión `.preview` los mantiene
fuera de todo lo que Python importa y de lo que alembic escanea, así que el
backend arranca normalmente con ellos presentes.

El código real (`v1.0/usuarios/models.py`, `v1.0/revision/*`,
`v1.0/ideas/models.py`) está en su estado previo a Fase 3/4, y
`alembic current` == `alembic heads` == `7e2c4a91b3f0`.

## Contenido

| Archivo | Qué es |
|---|---|
| `fase3-4-modelos-router-schemas.diff.preview` | Diff unificado contra `HEAD` de los 6 archivos que tocarían las Fases 3 y 4 |
| `b4d17c9e5a20_responsables_area_y_origen_asignacion.py.preview` | Migración de Fase 3 |
| `c9f3e820d114_historial_idea_y_reasignacion_con_aceptacion.py.preview` | Migración de Fase 4 |
| `fase-permisos-por-rol.md.preview` | Inventario completo de checks de autorización hardcodeados por rol + diseño de tabla `permisos_rol` configurable. Las 6 decisiones abiertas ya quedaron resueltas — incluye tabla de verificación fila por fila (22 checks) |
| `4d81f6c93a52_permisos_rol.py.preview` | Migración de la tabla `permisos_rol` + seed exacto (4 filas) que replica el comportamiento actual sin cambios |

### Advertencia sobre el diff

El diff se tomó contra `HEAD`, y **dos de los seis archivos
(`v1.0/usuarios/models.py` y `v1.0/revision/models.py`) tenían cambios en
vuelo sin commitear que no son parte de las Fases 3/4**. Esos hunks están
incluidos en el archivo. Son ~9 líneas en total y se distinguen porque no
mencionan `ResponsableArea`, `origen_asignacion`, `revisor_propuesto` ni
`HistorialIdea`.

Los otros cuatro archivos (`revision/service.py`, `revision/router.py`,
`revision/schemas.py`, `ideas/models.py`) sí contienen solo Fase 3/4.

## Para aplicarlo cuando se apruebe

```bash
git apply diseno-pendiente/fase3-4-modelos-router-schemas.diff.preview
cp diseno-pendiente/b4d17c9e5a20_*.preview \
   v1.0/alembic/versions/b4d17c9e5a20_responsables_area_y_origen_asignacion.py
cp diseno-pendiente/c9f3e820d114_*.preview \
   v1.0/alembic/versions/c9f3e820d114_historial_idea_y_reasignacion_con_aceptacion.py
```

El diff se generó antes del commit de Fase 1b, que también toca
`ideas/router.py` — no hay solape de archivos entre ambos, pero si `git
apply` falla por contexto, `git apply -3` resuelve con merge de tres vías.

**No corras `alembic upgrade head` sin antes cargar `responsables_area`.**
La tabla nace vacía y, mientras lo esté, `_buscar_encargado_activo` no
resuelve a nadie y toda idea nueva cae en `pendiente_asignacion`. Falta el
seed con los datos reales del negocio.

## Decisiones abiertas

- Fase 3: ¿el mapeo determinístico cubre también idea → CAB en
  `clasificacion/`, o solo el revisor?
- Fase 4: el plazo de expiración quedó en 3 días **hábiles**, sin calendario
  de feriados (no existe en el sistema para los 4 países).
- Fase 4: la notificación es solo badge in-app. `notificaciones/` tiene el
  envío de correo en stub, sin credenciales SMTP.
