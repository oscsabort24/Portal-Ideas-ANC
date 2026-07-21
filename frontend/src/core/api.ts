import { InteractionRequiredAuthError } from '@azure/msal-browser'
import { apiTokenRequest, azureAdConfigurado } from './authConfig'
import { msalInstance } from './AuthProvider'
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
  if (res.status === 204) {
    return undefined as T
  }
  const cuerpo = await res.text()
  return (cuerpo ? JSON.parse(cuerpo) : undefined) as T
}

/**
 * Header de autenticación para cada request: token real de Microsoft si hay
 * sesión MSAL activa (azureAdConfigurado), o X-Usuario-Id en modo simulado
 * (desarrollo local sin Azure AD configurado) — ver
 * usuarios/dependencies.py:obtener_usuario_actual en el backend, que acepta
 * ambos con la misma prioridad.
 *
 * Si acquireTokenSilent requiere interacción (consentimiento vencido o
 * revocado), se redirige a Microsoft para renovarlo en vez de dejar fallar
 * la llamada silenciosamente.
 */
async function construirHeadersAuth(): Promise<Record<string, string>> {
  if (azureAdConfigurado && msalInstance) {
    const cuenta = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]
    if (cuenta) {
      try {
        const { accessToken } = await msalInstance.acquireTokenSilent({ ...apiTokenRequest, account: cuenta })
        return { Authorization: `Bearer ${accessToken}` }
      } catch (err) {
        if (err instanceof InteractionRequiredAuthError) {
          await msalInstance.acquireTokenRedirect({ ...apiTokenRequest, account: cuenta })
          // La página navega fuera durante el redirect — no hay token que devolver aquí.
          return {}
        }
        throw err
      }
    }
  }
  return { 'X-Usuario-Id': String(USUARIO_ACTUAL.id) }
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, { headers })
  return manejarRespuesta<T>(res)
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  })
  return manejarRespuesta<T>(res)
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiDelete(path: string): Promise<void> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, {
    method: 'DELETE',
    headers,
  })
  if (!res.ok) {
    throw new Error(await extraerMensajeError(res))
  }
}
