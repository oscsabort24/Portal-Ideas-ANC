import type { Idea } from '../ideas/types'
import type { TipoCAB } from '../usuarios/types'

export type EstadoClasificacion = 'pendiente_clasificacion' | 'clasificada'

export const ETIQUETA_ESTADO_CLASIFICACION: Record<EstadoClasificacion, string> = {
  pendiente_clasificacion: 'Pendiente de clasificación',
  clasificada: 'Clasificada',
}

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface Clasificacion {
  id: number
  idea_id: number
  estado: EstadoClasificacion
  clasificacion: TipoCAB | null
  clasificado_por_id: number | null
  fecha_clasificacion: string | null
  creado_en: string
}

export interface ClasificacionDetalle extends Clasificacion {
  idea: Idea
  clasificado_por: UsuarioResumen | null
}
