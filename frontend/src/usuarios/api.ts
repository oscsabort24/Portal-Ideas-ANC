import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from '../core/api'
import type {
  Departamento,
  MiembroCAB,
  MiembroCABDetalle,
  PermisoRol,
  PermisoRolActualizar,
  Puesto,
  Usuario,
  UsuarioCreate,
  UsuarioUpdate,
} from './types'

export function listarUsuarios(): Promise<Usuario[]> {
  return apiGet<Usuario[]>('/usuarios')
}

export function obtenerUsuario(id: number): Promise<Usuario> {
  return apiGet<Usuario>(`/usuarios/${id}`)
}

export function obtenerUsuarioPorCorreo(correo: string): Promise<Usuario> {
  return apiGet<Usuario>(`/usuarios/por-correo?correo=${encodeURIComponent(correo)}`)
}

/**
 * Accesos rápidos de desarrollo (ver core/dev_router.py). Solo responde si
 * el backend tiene ENTORNO=development — en producción el endpoint no existe.
 */
export function devLogin(correo: string): Promise<Usuario> {
  return apiPost<Usuario>('/auth/dev-login', { correo })
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

export function listarPuestos(): Promise<Puesto[]> {
  return apiGet<Puesto[]>('/usuarios/puestos/')
}

export function crearPuesto(payload: { nombre: string; departamento_id: number }): Promise<Puesto> {
  return apiPost<Puesto>('/usuarios/puestos/', payload)
}

export function actualizarPuesto(
  id: number,
  cambios: { nombre?: string; departamento_id?: number }
): Promise<Puesto> {
  return apiPatch<Puesto>(`/usuarios/puestos/${id}`, cambios)
}

export function actualizarPuestoUnico(id: number, esUnicoPorPais: boolean): Promise<Puesto> {
  return apiPatch<Puesto>(`/usuarios/puestos/${id}/unico`, { es_unico_por_pais: esUnicoPorPais })
}

export function eliminarPuesto(id: number): Promise<void> {
  return apiDelete(`/usuarios/puestos/${id}`)
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

/** Permisos efectivos (resueltos) del usuario actual — no la tabla cruda. */
export function misPermisos(): Promise<Record<string, boolean>> {
  return apiGet<Record<string, boolean>>('/me/permisos')
}

/** Qué roles tienen un permiso dado — usado para armar selectores (ej. quién
 * puede ser revisor) sin hardcodear la lista de roles en el cliente. */
export function rolesConPermiso(clavePermiso: string): Promise<string[]> {
  return apiGet<string[]>(`/permisos-rol/roles/${clavePermiso}`)
}

export function listarPermisosRol(): Promise<PermisoRol[]> {
  return apiGet<PermisoRol[]>('/permisos-rol')
}

export function guardarPermisosRol(permisos: PermisoRolActualizar[]): Promise<PermisoRol[]> {
  return apiPut<PermisoRol[]>('/permisos-rol', { permisos })
}
