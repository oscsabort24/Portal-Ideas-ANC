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
  colaborador: 'Puede crear y ver sus propias ideas.',
  encargado_area: 'Además, revisa ideas asignadas de su departamento (aprobar, pedir cambios, reasignar).',
  gerente: 'Rol jerárquico general — hoy no tiene permisos especiales propios más allá de los de colaborador, salvo que además sea miembro de un CAB.',
  admin: 'Gestión completa de usuarios, departamentos, puestos, CAB, criterios de IA y notificaciones.',
}

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
