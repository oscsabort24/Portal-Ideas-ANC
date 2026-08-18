import { apiGet, apiPost, apiPut } from '../core/api'
import type { CoberturaDepartamento, CriterioIA, GuardarCriterioRequest, PinDefinir, TipoCriterio } from './types'

export function obtenerEstadoPin(): Promise<{ tiene_pin: boolean }> {
  return apiGet<{ tiene_pin: boolean }>('/criterios/pin/estado')
}

export function definirPin(payload: PinDefinir): Promise<void> {
  return apiPost<void>('/criterios/pin', payload)
}

export function obtenerCriterioActivo(tipo: TipoCriterio, departamentoId?: number): Promise<CriterioIA> {
  const query = departamentoId != null ? `?departamento_id=${departamentoId}` : ''
  return apiGet<CriterioIA>(`/criterios/${tipo}${query}`)
}

export function obtenerHistorial(tipo: TipoCriterio, departamentoId?: number): Promise<CriterioIA[]> {
  const query = departamentoId != null ? `?departamento_id=${departamentoId}` : ''
  return apiGet<CriterioIA[]>(`/criterios/${tipo}/historial${query}`)
}

export function guardarCriterio(tipo: TipoCriterio, payload: GuardarCriterioRequest): Promise<CriterioIA> {
  return apiPut<CriterioIA>(`/criterios/${tipo}`, payload)
}

export function obtenerCoberturaEntrevista(): Promise<CoberturaDepartamento[]> {
  return apiGet<CoberturaDepartamento[]>('/criterios/entrevista/cobertura')
}
