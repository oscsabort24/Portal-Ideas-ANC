import type { Idea } from '../ideas/types'

export type EstadoRevision = 'pendiente_asignacion' | 'pendiente_revision' | 'aprobada' | 'cambios_solicitados'

export const ETIQUETA_ESTADO_REVISION: Record<EstadoRevision, string> = {
  pendiente_asignacion: 'Pendiente de asignación',
  pendiente_revision: 'Pendiente de revisión',
  aprobada: 'Aprobada',
  cambios_solicitados: 'Cambios solicitados',
}

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
  fecha_asignacion: string | null
  fecha_resolucion: string | null
}

export interface RevisionDetalle extends Revision {
  idea: Idea
  revisor: UsuarioResumen | null
}
