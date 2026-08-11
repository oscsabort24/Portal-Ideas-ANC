export type TipoCriterio = 'clasificacion' | 'asignacion_revisor'

export const ETIQUETA_TIPO_CRITERIO: Record<TipoCriterio, string> = {
  clasificacion: 'Clasificación',
  asignacion_revisor: 'Asignación de revisor',
}

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface DocumentoCriterio {
  id: number
  tipo: TipoCriterio
  nombre_archivo: string
  version: number
  activo: boolean
  contenido: string | null
  descripcion: string | null
  subido_por: UsuarioResumen
  subido_en: string
  actualizado_por: UsuarioResumen | null
  actualizado_en: string | null
}

export interface PinDefinir {
  pin_actual?: string
  pin_nuevo: string
}

export interface DocumentoCriterioEditar {
  contenido?: string
  descripcion?: string
  pin: string
}
