import { apiDelete, apiGet, apiPatch, apiPost } from '../core/api'
import type { Departamento, MiembroCAB, MiembroCABDetalle, Usuario, UsuarioCreate, UsuarioUpdate } from './types'

export function listarUsuarios(): Promise<Usuario[]> {
  return apiGet<Usuario[]>('/usuarios')
}

export function obtenerUsuario(id: number): Promise<Usuario> {
  return apiGet<Usuario>(`/usuarios/${id}`)
}

export function crearUsuario(payload: UsuarioCreate): Promise<Usuario> {
  return apiPost<Usuario>('/usuarios', payload)
}

export function actualizarUsuario(id: number, cambios: UsuarioUpdate): Promise<Usuario> {
  return apiPatch<Usuario>(`/usuarios/${id}`, cambios)
}

export function listarDepartamentos(): Promise<Departamento[]> {
  return apiGet<Departamento[]>('/usuarios/departamentos/')
}

export function crearDepartamento(payload: { nombre: string }): Promise<Departamento> {
  return apiPost<Departamento>('/usuarios/departamentos/', payload)
}

export function actualizarDepartamento(id: number, cambios: { nombre: string }): Promise<Departamento> {
  return apiPatch<Departamento>(`/usuarios/departamentos/${id}`, cambios)
}

export function eliminarDepartamento(id: number): Promise<void> {
  return apiDelete(`/usuarios/departamentos/${id}`)
}

export function listarMiembrosCab(): Promise<MiembroCABDetalle[]> {
  return apiGet<MiembroCABDetalle[]>('/usuarios/cab/')
}

export function agregarMiembroCab(payload: {
  usuario_id: number
  tipo_cab: MiembroCAB['tipo_cab']
}): Promise<MiembroCAB> {
  return apiPost<MiembroCAB>('/usuarios/cab/', payload)
}

export function quitarMiembroCab(id: number): Promise<void> {
  return apiDelete(`/usuarios/cab/${id}`)
}
