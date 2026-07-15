export type EtapaEscalamiento = 'revision' | 'clasificacion' | 'comites'

export const ETIQUETA_ETAPA: Record<EtapaEscalamiento, string> = {
  revision: 'Revisión',
  clasificacion: 'Clasificación',
  comites: 'Comités',
}

export const ORDEN_ETAPAS: EtapaEscalamiento[] = ['revision', 'clasificacion', 'comites']

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface ConfiguracionEscalamiento {
  etapa: EtapaEscalamiento
  plazo_dias: number | null
  responsable_id: number | null
  responsable: UsuarioResumen | null
  actualizado_en: string
}

export interface ConfiguracionEscalamientoUpdate {
  plazo_dias: number | null
  responsable_id: number | null
}

export interface IdeaResumen {
  id: number
  titulo: string
}

export interface NotificacionEscalamiento {
  id: number
  etapa: EtapaEscalamiento
  idea_id: number
  idea: IdeaResumen
  responsable_id: number | null
  responsable: UsuarioResumen | null
  dias_transcurridos: number
  generada_en: string
  enviada: boolean
}

export interface RevisarResultado {
  notificaciones_generadas: number
  notificaciones: NotificacionEscalamiento[]
}
