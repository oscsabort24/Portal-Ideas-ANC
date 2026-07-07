const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function manejarRespuesta<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const cuerpo = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${cuerpo}`)
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
