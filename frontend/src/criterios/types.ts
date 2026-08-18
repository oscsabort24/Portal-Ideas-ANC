export type TipoCriterio = 'clasificacion' | 'asignacion_revisor' | 'entrevista'

export const ETIQUETA_TIPO_CRITERIO: Record<TipoCriterio, string> = {
  clasificacion: 'Clasificación',
  asignacion_revisor: 'Asignación de revisor',
  entrevista: 'Entrevista',
}

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface CriterioIA {
  id: number
  tipo: TipoCriterio
  departamento_id: number | null
  version: number
  activo: boolean
  contenido: string
  descripcion: string | null
  creado_por: UsuarioResumen
  creado_en: string
}

export interface PinDefinir {
  pin_actual?: string
  pin_nuevo: string
}

export interface GuardarCriterioRequest {
  contenido: string
  descripcion?: string
  departamento_id?: number | null
  pin: string
}

export interface CoberturaDepartamento {
  departamento_id: number
  nombre: string
  tiene_excepcion: boolean
}
