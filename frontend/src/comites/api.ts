import { apiGet, apiPost, apiPut } from '../core/api'
import type {
  ComiteIdea,
  ComiteIdeaDetalle,
  DepartamentoVisible,
  EstadoComite,
  RiceEvaluacion,
  RiceEvaluacionRequest,
} from './types'

export function colaComite(estado: EstadoComite = 'pendiente'): Promise<ComiteIdeaDetalle[]> {
  return apiGet<ComiteIdeaDetalle[]>(`/comites/cola?estado=${estado}`)
}

export function misDepartamentos(): Promise<DepartamentoVisible[]> {
  return apiGet<DepartamentoVisible[]>('/comites/mis-departamentos')
}

export function aprobar(ideaId: number): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/aprobar`, {})
}

export function rechazar(ideaId: number, motivoRechazo: string): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/rechazar`, { motivo_rechazo: motivoRechazo })
}

export function reasignar(ideaId: number, nuevoAsignadoId: number, motivo?: string): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/reasignar`, { nuevo_asignado_id: nuevoAsignadoId, motivo })
}

export function aceptarReasignacion(ideaId: number): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/aceptar-reasignacion`, {})
}

export function rechazarReasignacion(ideaId: number, motivo: string): Promise<ComiteIdea> {
  return apiPost<ComiteIdea>(`/comites/${ideaId}/rechazar-reasignacion`, { motivo })
}

export function obtenerRice(ideaId: number): Promise<RiceEvaluacion> {
  return apiGet<RiceEvaluacion>(`/comites/${ideaId}/rice`)
}

export function guardarRice(ideaId: number, payload: RiceEvaluacionRequest): Promise<RiceEvaluacion> {
  return apiPut<RiceEvaluacion>(`/comites/${ideaId}/rice`, payload)
}
