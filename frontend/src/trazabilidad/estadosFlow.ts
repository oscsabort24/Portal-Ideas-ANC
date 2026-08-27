import type { EstadoFlow } from './types'

// Mismo orden que trazabilidad/service.py:ESTADOS_FLOW en el backend — las
// columnas de la matriz y los nodos del pipeline siguen este orden.
export const ORDEN_ESTADOS_FLOW: EstadoFlow[] = [
  'borrador',
  'revision_pendiente_asignacion',
  'revision_en_curso',
  'revision_cambios_solicitados',
  'revision_rechazada',
  'clasificacion_pendiente',
  'comite_en_cola',
  'comite_rechazada',
  'comite_aprobada_sin_documentos',
  'documentos_en_generacion',
  'documentos_completos',
]

export const ETIQUETA_ESTADO_FLOW: Record<EstadoFlow, string> = {
  borrador: 'Borrador',
  revision_pendiente_asignacion: 'Rev. sin asignar',
  revision_en_curso: 'En revisión',
  revision_cambios_solicitados: 'Cambios solicitados',
  revision_rechazada: 'Rechazada en revisión',
  clasificacion_pendiente: 'Pend. clasificación',
  comite_en_cola: 'En cola de comité',
  comite_rechazada: 'Rechazada',
  comite_aprobada_sin_documentos: 'Aprobada, sin docs.',
  documentos_en_generacion: 'Docs. en generación',
  documentos_completos: 'Docs. completos',
}

// ─────────────────────────────────────────────────────────────────────────
// Mapeo a los 5 pasos del stepper de progreso que ve el colaborador.
//
// Vive en el frontend a propósito: `estado_flow` es el dato (lo produce
// trazabilidad/service.py:_derivar_estado); cuántos círculos se dibujan y de
// qué color es decisión de presentación. El backend no tiene por qué saber
// que existe un stepper.
//
// La red contra desincronización es el Record<EstadoFlow, …>: TypeScript
// exige las 11 claves, así que un estado nuevo en el backend no puede llegar
// acá sin que alguien decida su paso y su tipo.
// ─────────────────────────────────────────────────────────────────────────

/** Los 5 hitos del proceso, en orden. */
export const PASOS_PROGRESO = [
  'Enviada',
  'Revisión de área',
  'Clasificación',
  'Comité',
  'Documentos',
] as const

/**
 * - `avance`   : va progresando, nadie tiene que hacer nada distinto.
 * - `accion`   : la pelota está del lado del AUTOR (pidieron cambios).
 * - `rechazo`  : terminó mal en este paso; los siguientes no van a ocurrir.
 * - `completo` : llegó al final del proceso.
 * - `sin_iniciar`: todavía en borrador, no arrancó el circuito.
 */
export type TipoProgreso = 'sin_iniciar' | 'avance' | 'accion' | 'rechazo' | 'completo'

export interface ProgresoIdea {
  /** 1..5, o 0 si todavía no arrancó (borrador). */
  paso: number
  tipo: TipoProgreso
}

export const PROGRESO_POR_ESTADO: Record<EstadoFlow, ProgresoIdea> = {
  // Paso 0 — todavía no salió de borrador, no hay RevisionIdea.
  borrador: { paso: 0, tipo: 'sin_iniciar' },

  // Paso 2 — Revisión de área. El paso 1 ("Enviada") nunca es el actual:
  // RevisionIdea se crea atómicamente al enviar, así que la idea pasa de
  // borrador a revisión sin escala. Existe como hito completado.
  revision_pendiente_asignacion: { paso: 2, tipo: 'avance' },
  revision_en_curso: { paso: 2, tipo: 'avance' },
  revision_cambios_solicitados: { paso: 2, tipo: 'accion' },
  revision_rechazada: { paso: 2, tipo: 'rechazo' },

  // Paso 3 — Clasificación. No tiene rechazo ni vuelta atrás.
  clasificacion_pendiente: { paso: 3, tipo: 'avance' },

  // Paso 4 — Comité.
  comite_en_cola: { paso: 4, tipo: 'avance' },
  comite_rechazada: { paso: 4, tipo: 'rechazo' },

  // Paso 5 — Documentos. "Aprobada sin documentos" ya es paso 5: el comité
  // dijo que sí y lo único que falta es que se generen.
  comite_aprobada_sin_documentos: { paso: 5, tipo: 'avance' },
  documentos_en_generacion: { paso: 5, tipo: 'avance' },
  documentos_completos: { paso: 5, tipo: 'completo' },
}

/** Frase de acción bajo el stepper. null = el estado se explica solo. */
export const ACCION_POR_ESTADO: Partial<Record<EstadoFlow, string>> = {
  revision_cambios_solicitados: 'El revisor pidió cambios — respondé en el chat de la idea.',
  revision_rechazada: 'El revisor de área no aprobó esta idea. La decisión es final.',
  comite_rechazada: 'El comité no aprobó esta idea.',
  documentos_completos: 'Los 6 documentos formales están listos para descargar.',
}

/**
 * Porcentaje de avance que se le muestra al colaborador en la página de
 * inicio ("Tus ideas en curso").
 *
 * POR ESTADO, no derivado de `paso`. La fórmula obvia —(paso / 5) * 100—
 * falla porque los pasos agrupan varios estados: el paso 5 contiene
 * `comite_aprobada_sin_documentos`, `documentos_en_generacion` y
 * `documentos_completos`, así que los tres darían 100%. Los dos primeros NO
 * están terminados, y son justo los visibles (el 100% real queda filtrado
 * por ser terminal). Le diría al autor "tu idea está al 100%" con los
 * documentos todavía sin generar.
 *
 * Tres propiedades que la tabla garantiza y la fórmula no:
 *   - es monótona;
 *   - nada llega a 100% sin estar terminado;
 *   - `revision_cambios_solicitados` NO retrocede la barra — la idea nunca
 *     salió del paso 2, el ida y vuelta ocurre DENTRO del paso (mismo
 *     criterio que el stepper).
 *
 * Los números son un juicio, no una medición: no pretenden ser
 * proporcionales al tiempo real de cada etapa, solo dar una sensación
 * honesta de avance.
 */
export const PORCENTAJE_POR_ESTADO: Record<EstadoFlow, number> = {
  borrador: 0,
  revision_pendiente_asignacion: 15,
  revision_en_curso: 30,
  revision_cambios_solicitados: 30,
  revision_rechazada: 30, // terminal negativo: no se muestra en "en curso"
  clasificacion_pendiente: 50,
  comite_en_cola: 65,
  comite_rechazada: 65, // terminal negativo: no se muestra en "en curso"
  comite_aprobada_sin_documentos: 85,
  documentos_en_generacion: 95,
  documentos_completos: 100,
}

/**
 * Estados en los que la idea sigue viva en el proceso.
 *
 * Excluye los tres terminales: `documentos_completos` (positivo),
 * `revision_rechazada` y `comite_rechazada` (negativos). `borrador` también
 * queda afuera acá porque la página de inicio ya lo cubre con su propio
 * aviso de "idea sin terminar", que lleva a continuar la entrevista.
 */
export const ESTADOS_ACTIVOS: ReadonlySet<EstadoFlow> = new Set<EstadoFlow>([
  'revision_pendiente_asignacion',
  'revision_en_curso',
  'revision_cambios_solicitados',
  'clasificacion_pendiente',
  'comite_en_cola',
  'comite_aprobada_sin_documentos',
  'documentos_en_generacion',
])

export function esEstadoActivo(estado: EstadoFlow | null): boolean {
  return estado !== null && ESTADOS_ACTIVOS.has(estado)
}
