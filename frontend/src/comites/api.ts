import { apiGet, apiPost } from '../core/api'
import type { TipoCAB } from '../usuarios/types'
import type { ComiteIdea, ComiteIdeaDetalle } from './types'

export function colaComite(tipoCab: TipoCAB): Promise<ComiteIdeaDetalle[]> {
  return apiGet<ComiteIdeaDetalle[]>(`/comites/${tipoCab}/cola`)
}

export function aprobar(ideaId: number): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/aprobar`, {})
}

export function rechazar(ideaId: number, motivoRechazo: string): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/rechazar`, { motivo_rechazo: motivoRechazo })
}
