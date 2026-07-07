import { USUARIO_ACTUAL } from './UsuarioActualContext'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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

async function manejarRespuesta<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(await extraerMensajeError(res))
  }
  return res.json() as Promise<T>
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  return manejarRespuesta<T>(res)
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'DELETE',
    headers: { 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
  })
  if (!res.ok) {
    throw new Error(await extraerMensajeError(res))
  }
}
