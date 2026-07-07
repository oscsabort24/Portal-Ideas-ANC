import { apiGet, apiPost } from '../core/api'
import type { Departamento, MiembroCAB, Usuario } from './types'

export function listarUsuarios(): Promise<Usuario[]> {
  return apiGet<Usuario[]>('/usuarios')
}

export function obtenerUsuario(id: number): Promise<Usuario> {
  return apiGet<Usuario>(`/usuarios/${id}`)
}

export function listarDepartamentos(): Promise<Departamento[]> {
  return apiGet<Departamento[]>('/usuarios/departamentos/')
}

export function agregarMiembroCab(payload: {
  usuario_id: number
  tipo_cab: MiembroCAB['tipo_cab']
}): Promise<MiembroCAB> {
  return apiPost<MiembroCAB>('/usuarios/cab/', payload)
}
