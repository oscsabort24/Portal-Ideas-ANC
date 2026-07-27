import { apiGet, apiPatch, apiPost, apiPostFormData, construirHeadersAuth } from '../core/api'
import type { DocumentoCriterio, DocumentoCriterioEditar, PinDefinir, TipoCriterio } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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

/**
 * Descarga el documento activo trayéndolo como blob en vez de navegar a la
 * URL con un <a href>. GET /criterios/{tipo}/descargar ahora exige rol admin,
 * y una navegación del navegador no puede mandar el header Authorization —
 * el link plano daría 401. Mismo patrón que documentos/api.ts:descargarBlob.
 */
export async function descargarDocumentoActivo(tipo: TipoCriterio, nombreArchivo: string): Promise<void> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}/criterios/${tipo}/descargar`, { headers })
  if (!res.ok) {
    const cuerpo = await res.text()
    try {
      const json = JSON.parse(cuerpo)
      if (typeof json.detail === 'string') throw new Error(json.detail)
    } catch (err) {
      if (err instanceof Error && err.message) throw err
    }
    throw new Error(cuerpo || `${res.status} ${res.statusText}`)
  }

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombreArchivo
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
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

export function editarDocumento(id: number, payload: DocumentoCriterioEditar): Promise<DocumentoCriterio> {
  return apiPatch<DocumentoCriterio>(`/criterios/${id}`, payload)
}
