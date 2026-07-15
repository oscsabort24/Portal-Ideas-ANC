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

export function enviarMensaje(ideaId: number, contenido: string): Promise<RespuestaEntrevista> {
  return apiPost<RespuestaEntrevista>(`/ideas/${ideaId}/mensajes`, { contenido })
}

export function obtenerLineaTiempo(ideaId: number): Promise<EventoLineaTiempo[]> {
  return apiGet<EventoLineaTiempo[]>(`/ideas/${ideaId}/linea-tiempo`)
}
