export type RolUsuario = 'colaborador' | 'encargado_area' | 'gerente' | 'admin'
export type TipoCAB = 'innovacion' | 'transformacion_digital'

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
