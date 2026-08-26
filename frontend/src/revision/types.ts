import type { Idea } from '../ideas/types'

export type EstadoRevision =
  | 'pendiente_asignacion'
  | 'pendiente_revision'
  | 'aprobada'
  | 'cambios_solicitados'
  | 'pendiente_aceptacion_reasignacion'
  | 'rechazada'

export const ETIQUETA_ESTADO_REVISION: Record<EstadoRevision, string> = {
  pendiente_asignacion: 'Pendiente de asignación',
  pendiente_revision: 'Pendiente de revisión',
  aprobada: 'Aprobada',
  cambios_solicitados: 'Cambios solicitados',
  pendiente_aceptacion_reasignacion: 'Reasignación pendiente de aceptación',
  rechazada: 'Rechazada',
}

export type OrigenAsignacion = 'mapeo_area' | 'fallback_departamento_autor' | 'manual' | 'sin_asignar'

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface Revision {
  id: number
  idea_id: number
  revisor_id: number | null
  estado: EstadoRevision
  retroalimentacion: string | null
  motivo_rechazo: string | null
  fecha_asignacion: string | null
  fecha_resolucion: string | null
  origen_asignacion: OrigenAsignacion
  propuesto_a_id: number | null
  reasignacion_solicitada_por_id: number | null
  fecha_solicitud_reasignacion: string | null
}

export interface RevisionDetalle extends Revision {
  idea: Idea
  revisor: UsuarioResumen | null
  propuesto_a: UsuarioResumen | null
  reasignacion_solicitada_por: UsuarioResumen | null
}

/** Una idea que este revisor aprobó y que el comité rechazó después.
 *  Ver revision/schemas.py:RevisionRechazadaEnComiteOut. */
export interface RevisionRechazadaEnComite {
  idea: Idea
  motivo_rechazo: string | null
  fecha_resolucion: string | null
  rechazada_por: UsuarioResumen | null
}
