import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from '../core/api'
import type {
  ActualizarDepartamentosMiembroCABRequest,
  Departamento,
  MiembroCABDetalle,
  PermisoRol,
  PermisoRolActualizar,
  Puesto,
  Usuario,
  UsuarioBasico,
  UsuarioCreate,
  UsuarioUpdate,
} from './types'

export function listarUsuarios(): Promise<Usuario[]> {
  return apiGet<Usuario[]>('/usuarios')
}

// Sin correo ni rol — para pickers de "elegí una persona" accesibles a
// cualquier identidad autenticada (no solo admin), ver diagnóstico #2:
// listarUsuarios() completo ahora requiere admin.
export function listarUsuariosDirectorioBasico(): Promise<UsuarioBasico[]> {
  return apiGet<UsuarioBasico[]>('/usuarios/directorio-basico')
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

/** Alta en un solo paso. `tipo_cab` ya no se manda (el backend aplica un
 *  default de compatibilidad) y `departamento_ids` define el alcance desde
 *  el alta — lista vacía = ve todos los departamentos. La respuesta es el
 *  detalle completo, con usuario y departamentos ya resueltos. */
export function agregarMiembroCab(payload: {
  usuario_id: number
  departamento_ids: number[]
}): Promise<MiembroCABDetalle> {
  return apiPost<MiembroCABDetalle>('/usuarios/cab/', payload)
}

export function quitarMiembroCab(id: number): Promise<void> {
  return apiDelete(`/usuarios/cab/${id}`)
}

export function actualizarDepartamentosMiembroCab(
  miembroId: number,
  payload: ActualizarDepartamentosMiembroCABRequest,
): Promise<MiembroCABDetalle> {
  return apiPut<MiembroCABDetalle>(`/usuarios/cab/${miembroId}/departamentos`, payload)
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
