import { apiGet, apiPost } from '../core/api'
import type { TipoCAB } from '../usuarios/types'
import type { Clasificacion, ClasificacionDetalle } from './types'

export function clasificacionesPendientes(): Promise<ClasificacionDetalle[]> {
  return apiGet<ClasificacionDetalle[]>('/clasificacion/pendientes')
}

export function clasificar(ideaId: number, clasificacion: TipoCAB): Promise<Clasificacion> {
  return apiPost<Clasificacion>(`/clasificacion/${ideaId}/clasificar`, { clasificacion })
}
