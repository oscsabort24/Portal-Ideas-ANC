import { apiGet, apiPost, apiPut } from '../core/api'
import type { TipoCAB } from '../usuarios/types'
import type { ComiteIdea, ComiteIdeaDetalle, RiceEvaluacion, RiceEvaluacionRequest } from './types'

export function colaComite(tipoCab: TipoCAB): Promise<ComiteIdeaDetalle[]> {
  return apiGet<ComiteIdeaDetalle[]>(`/comites/${tipoCab}/cola`)
}

export function aprobar(ideaId: number): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/aprobar`, {})
}

export function rechazar(ideaId: number, motivoRechazo: string): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/rechazar`, { motivo_rechazo: motivoRechazo })
}

export function obtenerRice(ideaId: number): Promise<RiceEvaluacion> {
  return apiGet<RiceEvaluacion>(`/comites/${ideaId}/rice`)
}

export function guardarRice(ideaId: number, payload: RiceEvaluacionRequest): Promise<RiceEvaluacion> {
  return apiPut<RiceEvaluacion>(`/comites/${ideaId}/rice`, payload)
}
