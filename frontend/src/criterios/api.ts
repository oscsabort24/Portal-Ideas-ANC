import { apiGet, apiPost, apiPostFormData } from '../core/api'
import type { DocumentoCriterio, PinDefinir, TipoCriterio } from './types'

export function obtenerEstadoPin(): Promise<{ tiene_pin: boolean }> {
  return apiGet<{ tiene_pin: boolean }>('/criterios/pin/estado')
}

export function definirPin(payload: PinDefinir): Promise<void> {
  return apiPost<void>('/criterios/pin', payload)
}

export function obtenerDocumentoActivo(tipo: TipoCriterio): Promise<DocumentoCriterio> {
  return apiGet<DocumentoCriterio>(`/criterios/${tipo}`)
}

export function obtenerHistorial(tipo: TipoCriterio): Promise<DocumentoCriterio[]> {
  return apiGet<DocumentoCriterio[]>(`/criterios/${tipo}/historial`)
}

export function urlDescarga(tipo: TipoCriterio): string {
  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
  return `${API_URL}/criterios/${tipo}/descargar`
}

export function subirDocumento(
  tipo: TipoCriterio,
  archivo: File,
  pin: string
): Promise<DocumentoCriterio> {
  const formData = new FormData()
  formData.append('archivo', archivo)
  formData.append('pin', pin)
  return apiPostFormData<DocumentoCriterio>(`/criterios/${tipo}`, formData)
}
