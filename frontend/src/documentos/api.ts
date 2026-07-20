import { apiGet, apiPost } from '../core/api'
import { USUARIO_ACTUAL } from '../core/UsuarioActualContext'
import type { DocumentoGenerado, PendientesDocumentos, TipoDocumento } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function listarDocumentos(ideaId: number): Promise<DocumentoGenerado[]> {
  return apiGet<DocumentoGenerado[]>(`/documentos/${ideaId}`)
}

export function obtenerPendientes(ideaId: number): Promise<PendientesDocumentos> {
  return apiGet<PendientesDocumentos>(`/documentos/${ideaId}/pendientes`)
}

export function generarDocumentos(ideaId: number, tipos: TipoDocumento[]): Promise<DocumentoGenerado[]> {
  return apiPost<DocumentoGenerado[]>(`/documentos/${ideaId}/generar`, { tipos })
}

async function extraerMensajeError(res: Response): Promise<string> {
  const cuerpo = await res.text()
  try {
    const json = JSON.parse(cuerpo)
    if (typeof json.detail === 'string') return json.detail
  } catch {
    // no era JSON, se usa el texto crudo
  }
  return cuerpo || `${res.status} ${res.statusText}`
}

function nombreArchivoDesdeHeader(res: Response, fallback: string): string {
  const header = res.headers.get('Content-Disposition')
  if (!header) return fallback

  // filename*=UTF-8''nombre%20codificado (RFC 6266) — preferido si viene presente.
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      // sigue al fallback de filename= plano
    }
  }

  const plainMatch = header.match(/filename="?([^"; ]+)"?/i)
  return plainMatch ? plainMatch[1] : fallback
}

async function descargarBlob(path: string, init: RequestInit, fallback: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...init.headers, 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
  })
  if (!res.ok) {
    throw new Error(await extraerMensajeError(res))
  }

  const nombreArchivo = nombreArchivoDesdeHeader(res, fallback)
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

export function descargarDocumento(ideaId: number, tipo: TipoDocumento): Promise<void> {
  return descargarBlob(`/documentos/${ideaId}/${tipo}/descargar`, {}, `${tipo}.docx`)
}

export function descargarZip(ideaId: number, tipos: TipoDocumento[]): Promise<void> {
  return descargarBlob(
    `/documentos/${ideaId}/descargar-zip`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipos }),
    },
    'documentos.zip',
  )
}
