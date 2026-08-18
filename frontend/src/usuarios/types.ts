export type RolUsuario = 'colaborador' | 'encargado_area' | 'gerente' | 'admin'
export type TipoCAB = 'innovacion' | 'transformacion_digital'
export type PaisUsuario = 'CR' | 'GT' | 'NI' | 'PE'
export type CompaniaUsuario = 'ANC_CAR' | 'RENTING' | 'RENTAS_INT'

export const ETIQUETA_ROL: Record<RolUsuario, string> = {
  colaborador: 'Colaborador',
  encargado_area: 'Encargado de área',
  gerente: 'Gerente',
  admin: 'Administrador',
}

export const DESCRIPCION_ROL: Record<RolUsuario, string> = {
  colaborador: 'Crea y ve solo sus propias ideas, y puede generar/regenerar los documentos de esas ideas mientras no exista un comité (CAB) para ellas.',
  encargado_area: 'Todo lo de Colaborador. Además, revisa las ideas asignadas de su departamento: puede aprobarlas, pedir cambios o reasignarlas.',
  gerente: 'Todo lo de Encargado de área. Además, ve todas las ideas del sistema (no solo las propias).',
  admin: 'Acceso total: gestiona usuarios, departamentos, puestos, miembros del CAB y notificaciones; es el único rol que puede subir/actualizar los criterios de IA; y no tiene las restricciones de generación de documentos que sí aplican a los demás roles.',
}

/** Orden fijo en que se muestran los roles en listados y en la página de
 * Roles y permisos (Organización) — de menor a mayor alcance. */
export const ROLES_ORDENADOS: RolUsuario[] = ['colaborador', 'encargado_area', 'gerente', 'admin']

export const ETIQUETA_PAIS: Record<PaisUsuario, string> = {
  CR: 'Costa Rica',
  GT: 'Guatemala',
  NI: 'Nicaragua',
  PE: 'Perú',
}

export const ETIQUETA_COMPANIA: Record<CompaniaUsuario, string> = {
  ANC_CAR: 'ANC Car',
  RENTING: 'Renting',
  RENTAS_INT: 'Rentas Internacionales',
}

export interface Departamento {
  id: number
  nombre: string
}

export interface Puesto {
  id: number
  nombre: string
  departamento_id: number
  es_unico_por_pais: boolean
}

export interface Usuario {
  id: number
  nombre: string
  correo: string
  rol: RolUsuario
  pais: PaisUsuario
  compania: CompaniaUsuario
  departamento_id: number | null
  puesto_id: number | null
  reporta_a_id: number | null
  activo: boolean
}

export type ClavePermiso =
  | 've_todas_las_ideas'
  | 've_flow_control'
  | 'es_revisor_elegible'
  | 'corrige_clasificacion'

export const ETIQUETA_PERMISO: Record<ClavePermiso, string> = {
  ve_todas_las_ideas: 'Ve todas las ideas del sistema (Panel de administración)',
  ve_flow_control: 'Ve Flow Control (Trazabilidad)',
  es_revisor_elegible: 'Puede ser asignado como revisor',
  corrige_clasificacion: 'Puede corregir la clasificación de una idea',
}

export const PERMISOS_ORDENADOS: ClavePermiso[] = [
  've_todas_las_ideas',
  've_flow_control',
  'es_revisor_elegible',
  'corrige_clasificacion',
]

/** Roles que se pueden configurar en la grilla de permisos — admin queda
 * afuera a propósito: siempre tiene todo, no es configurable. */
export const ROLES_CONFIGURABLES: RolUsuario[] = ['colaborador', 'encargado_area', 'gerente']

export interface PermisoRol {
  id: number
  rol: RolUsuario
  clave_permiso: ClavePermiso
  permitido: boolean
}

export interface PermisoRolActualizar {
  rol: RolUsuario
  clave_permiso: ClavePermiso
  permitido: boolean
}

export interface MiembroCAB {
  id: number
  usuario_id: number
  tipo_cab: TipoCAB
}

export interface MiembroCABDetalle extends MiembroCAB {
  usuario: Usuario
}

export interface UsuarioCreate {
  nombre: string
  correo: string
  pais: PaisUsuario
  compania: CompaniaUsuario
  departamento_id: number | null
  puesto_id: number
  reporta_a_id: number | null
}

export interface UsuarioUpdate {
  nombre?: string
  correo?: string
  rol?: RolUsuario
  pais?: PaisUsuario
  compania?: CompaniaUsuario
  departamento_id?: number | null
  puesto_id?: number | null
  reporta_a_id?: number | null
  activo?: boolean
}
