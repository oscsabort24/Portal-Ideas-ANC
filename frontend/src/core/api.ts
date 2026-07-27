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
 * revocado), se redirige a Microsoft para renovarlo Y SE LANZA: antes se
 * devolvía {} y el fetch salía igual, sin header Authorization. Contra un
 * endpoint protegido eso daba un 401 con mensaje confuso, y contra los
 * endpoints que no exigían autenticación la request se ejecutaba de verdad
 * pese a la sesión vencida. Lanzar corta la llamada; la navegación del
 * redirect ocurre de todas formas.
 */
export async function construirHeadersAuth(forzarRefresh = false): Promise<Record<string, string>> {
  if (azureAdConfigurado && msalInstance) {
    const cuenta = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]
    if (cuenta) {
      try {
        const { accessToken } = await msalInstance.acquireTokenSilent({
          ...apiTokenRequest,
          account: cuenta,
          forceRefresh: forzarRefresh,
        })
        return { Authorization: `Bearer ${accessToken}` }
      } catch (err) {
        if (err instanceof InteractionRequiredAuthError) {
          await msalInstance.acquireTokenRedirect({ ...apiTokenRequest, account: cuenta })
          throw new Error('Tu sesión venció. Te estamos redirigiendo a Microsoft para renovarla.')
        }
        throw err
      }
    }
  }
  return { 'X-Usuario-Id': String(USUARIO_ACTUAL.id) }
}

/** Solo hay token que renovar si MSAL está en juego; en modo simulado no. */
function haySesionMsal(): boolean {
  if (!azureAdConfigurado || !msalInstance) return false
  return (msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]) !== undefined
}

/**
 * Ejecuta la request con auth y, ante un 401, reintenta UNA vez con el token
 * refrescado a la fuerza. Si el reintento vuelve a dar 401, la sesión ya no
 * es recuperable en silencio y se manda a login.
 *
 * El reintento es seguro para los POST de este frontend: el único que crea
 * algo de forma no idempotente es POST /ideas/{id}/mensajes, que va con
 * Idempotency-Key (ver ideas/api.ts) — un reintento con la misma clave
 * devuelve el turno ya generado en vez de duplicarlo.
 */
async function solicitar(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = await construirHeadersAuth()
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...init.headers, ...headers } })
  if (res.status !== 401 || !haySesionMsal()) return res

  const headersRenovados = await construirHeadersAuth(true)
  const reintento = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...init.headers, ...headersRenovados },
  })
  if (reintento.status === 401) {
    await msalInstance!.loginRedirect(apiTokenRequest)
    throw new Error('Tu sesión venció. Te estamos redirigiendo para que inicies sesión de nuevo.')
  }
  return reintento
}

export async function apiGet<T>(path: string): Promise<T> {
  return manejarRespuesta<T>(await solicitar(path))
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
  headersExtra?: Record<string, string>,
): Promise<T> {
  const res = await solicitar(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headersExtra },
    body: JSON.stringify(body),
    signal,
  })
  return manejarRespuesta<T>(res)
}

export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  return manejarRespuesta<T>(await solicitar(path, { method: 'POST', body: formData }))
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await solicitar(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await solicitar(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return manejarRespuesta<T>(res)
}

export async function apiDelete(path: string): Promise<void> {
  const res = await solicitar(path, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(await extraerMensajeError(res))
  }
}
