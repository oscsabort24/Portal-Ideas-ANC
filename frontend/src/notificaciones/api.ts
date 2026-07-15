import { apiGet, apiPost, apiPut } from '../core/api'
import type {
  ConfiguracionEscalamiento,
  ConfiguracionEscalamientoUpdate,
  EtapaEscalamiento,
  NotificacionEscalamiento,
  RevisarResultado,
} from './types'

export function obtenerConfig(etapa: EtapaEscalamiento): Promise<ConfiguracionEscalamiento> {
  return apiGet<ConfiguracionEscalamiento>(`/notificaciones/config/${etapa}`)
}

export function actualizarConfig(
  etapa: EtapaEscalamiento,
  payload: ConfiguracionEscalamientoUpdate,
): Promise<ConfiguracionEscalamiento> {
  return apiPut<ConfiguracionEscalamiento>(`/notificaciones/config/${etapa}`, payload)
}

export function revisarVencidas(): Promise<RevisarResultado> {
  return apiPost<RevisarResultado>('/notificaciones/revisar', {})
}

export function listarHistorial(): Promise<NotificacionEscalamiento[]> {
  return apiGet<NotificacionEscalamiento[]>('/notificaciones')
}
