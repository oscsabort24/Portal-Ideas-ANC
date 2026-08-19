import { apiGet, apiPost } from '../core/api'
import type { Revision, RevisionDetalle } from './types'

export function misRevisiones(): Promise<RevisionDetalle[]> {
  return apiGet<RevisionDetalle[]>('/revision/mias')
}

export function revisionesSinAsignar(): Promise<RevisionDetalle[]> {
  return apiGet<RevisionDetalle[]>('/revision/sin-asignar')
}

export function asignarRevisor(ideaId: number, revisorId: number): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/asignar`, { revisor_id: revisorId })
}

export function aprobar(ideaId: number): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/aprobar`, {})
}

export function pedirCambios(ideaId: number, retroalimentacion: string): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/pedir-cambios`, { retroalimentacion })
}

export function reasignar(ideaId: number, nuevoRevisorId: number, motivo?: string): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/reasignar`, { nuevo_revisor_id: nuevoRevisorId, motivo })
}

export function aceptarReasignacion(ideaId: number): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/aceptar-reasignacion`, {})
}

export function rechazarReasignacion(ideaId: number, motivo: string): Promise<Revision> {
  return apiPost<Revision>(`/revision/${ideaId}/rechazar-reasignacion`, { motivo })
}
