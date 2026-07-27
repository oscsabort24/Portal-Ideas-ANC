import { apiGet, apiPost } from '../core/api'
import type { EstadoIdea, EventoLineaTiempo, Idea, IdeaDetalle, RespuestaEntrevista } from './types'

export function crearIdea(payload: { titulo: string; autor_id: number }): Promise<Idea> {
  return apiPost<Idea>('/ideas', payload)
}

export function obtenerIdea(id: number): Promise<IdeaDetalle> {
  return apiGet<IdeaDetalle>(`/ideas/${id}`)
}

export function listarIdeas(filtros: { autor_id?: number; estado?: EstadoIdea } = {}): Promise<Idea[]> {
  const params = new URLSearchParams()
  if (filtros.autor_id !== undefined) params.set('autor_id', String(filtros.autor_id))
  if (filtros.estado !== undefined) params.set('estado', filtros.estado)
  const query = params.toString()
  return apiGet<Idea[]>(`/ideas${query ? `?${query}` : ''}`)
}

export function enviarMensaje(ideaId: number, contenido: string, signal?: AbortSignal): Promise<RespuestaEntrevista> {
  return apiPost<RespuestaEntrevista>(`/ideas/${ideaId}/mensajes`, { contenido }, signal)
}

export function enviarIdea(ideaId: number): Promise<Idea> {
  return apiPost<Idea>(`/ideas/${ideaId}/enviar`, {})
}

export function obtenerLineaTiempo(ideaId: number): Promise<EventoLineaTiempo[]> {
  return apiGet<EventoLineaTiempo[]>(`/ideas/${ideaId}/linea-tiempo`)
}

export function obtenerResumen(ideaId: number): Promise<{ resumen: string; categoria_riesgo: string | null }> {
  return apiGet<{ resumen: string; categoria_riesgo: string | null }>(`/ideas/${ideaId}/resumen`)
}

export function preguntarSobreIdea(
  ideaId: number,
  pregunta: string,
  origen: 'revision' | 'comite',
): Promise<{ respuesta: string }> {
  return apiPost<{ respuesta: string }>(`/ideas/${ideaId}/preguntar`, { pregunta, origen })
}
