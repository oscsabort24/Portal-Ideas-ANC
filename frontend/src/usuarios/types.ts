export type RolUsuario = 'colaborador' | 'encargado_area' | 'gerente' | 'admin'
export type TipoCAB = 'innovacion' | 'transformacion_digital'

export const ETIQUETA_ROL: Record<RolUsuario, string> = {
  colaborador: 'Colaborador',
  encargado_area: 'Encargado de área',
  gerente: 'Gerente',
  admin: 'Administrador',
}

export interface Departamento {
  id: number
  nombre: string
}

export interface Usuario {
  id: number
  nombre: string
  correo: string
  rol: RolUsuario
  departamento_id: number | null
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
  departamento_id: number | null
  reporta_a_id: number | null
}

export interface UsuarioUpdate {
  nombre?: string
  correo?: string
  rol?: RolUsuario
  departamento_id?: number | null
  reporta_a_id?: number | null
  activo?: boolean
}
