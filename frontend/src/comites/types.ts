import type { Idea } from '../ideas/types'
import type { TipoCAB } from '../usuarios/types'

export type EstadoComite = 'pendiente' | 'aprobada' | 'rechazada'

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface ComiteIdea {
  id: number
  idea_id: number
  tipo_cab: TipoCAB
  estado: EstadoComite
  motivo_rechazo: string | null
  aprobada_o_rechazada_por_id: number | null
  fecha_resolucion: string | null
  creado_en: string
}

export interface ComiteIdeaDetalle extends ComiteIdea {
  idea: Idea
  aprobada_o_rechazada_por: UsuarioResumen | null
}
