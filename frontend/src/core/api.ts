import { InteractionRequiredAuthError } from '@azure/msal-browser'
import { apiTokenRequest } from './authConfig'
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

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
  })
  return manejarRespuesta<T>(res)
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
    body: formData,
  })
  return manejarRespuesta<T>(res)
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-Usuario-Id': String(USUARIO_ACTUAL.id) },
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

/**
 * PRUEBA AISLADA de la validación real de tokens Microsoft (core/auth.py) —
 * llama únicamente a GET /usuarios/me-seguro con un access token real de MSAL
 * (Authorization: Bearer), en vez de X-Usuario-Id. Ninguna otra función de
 * este archivo usa esto todavía: el resto del sistema sigue con X-Usuario-Id
 * sin cambios hasta que este camino se confirme funcionando end-to-end.
 */
export async function obtenerUsuarioActualSeguroDePrueba(): Promise<unknown> {
  if (!msalInstance) {
    throw new Error('MSAL no está configurado (azureAdConfigurado es false)')
  }
  const cuenta = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]
  if (!cuenta) {
    throw new Error('No hay ninguna cuenta de Microsoft activa — inicia sesión primero')
  }

  let resultadoToken
  try {
    resultadoToken = await msalInstance.acquireTokenSilent({ ...apiTokenRequest, account: cuenta })
  } catch (err) {
    if (err instanceof InteractionRequiredAuthError) {
      // El usuario no dio consentimiento todavía para el scope access_as_user
      // (ej. sesión iniciada antes de este cambio) — se pide interactivamente.
      // La página navega fuera durante el redirect, así que no hay nada más
      // que devolver aquí.
      await msalInstance.acquireTokenRedirect({ ...apiTokenRequest, account: cuenta })
      return undefined
    }
    throw err
  }

  const res = await fetch(`${API_URL}/usuarios/me-seguro`, {
    headers: { Authorization: `Bearer ${resultadoToken.accessToken}` },
  })
  return manejarRespuesta<unknown>(res)
}
