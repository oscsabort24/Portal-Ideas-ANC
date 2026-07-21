import type { Idea } from '../ideas/types'
import type { TipoCAB } from '../usuarios/types'

export type EstadoComite = 'pendiente' | 'aprobada' | 'rechazada'

export interface UsuarioResumen {
  id: number
  nombre: string
}

export interface ComiteIdea {
  id: number
  idea_id: number
  tipo_cab: TipoCAB
  estado: EstadoComite
  motivo_rechazo: string | null
  aprobada_o_rechazada_por_id: number | null
  fecha_resolucion: string | null
  creado_en: string
}

export interface ComiteIdeaDetalle extends ComiteIdea {
  idea: Idea
  aprobada_o_rechazada_por: UsuarioResumen | null
}

export type PresupuestoRango = '0' | '1-10000' | '10001-20000' | '20001-30000' | '+30000'
export type NivelImpactoConfianza = 'muy_bajo' | 'medio' | 'alto' | 'muy_alto'
export type NivelEsfuerzo = 'corto_plazo' | 'medio_plazo' | 'largo_plazo'
export type PrioridadRice = 'baja' | 'media' | 'alta'

export const ETIQUETA_PRESUPUESTO: Record<PresupuestoRango, string> = {
  '0': '$0 (Desarrollo interno)',
  '1-10000': '$1 - $10,000',
  '10001-20000': '$10,001 - $20,000',
  '20001-30000': '$20,001 - $30,000',
  '+30000': 'Más de $30,000',
}

export const ETIQUETA_IMPACTO_CONFIANZA: Record<NivelImpactoConfianza, string> = {
  muy_bajo: 'Muy bajo',
  medio: 'Medio',
  alto: 'Alto',
  muy_alto: 'Muy alto',
}

export const ETIQUETA_ESFUERZO: Record<NivelEsfuerzo, string> = {
  corto_plazo: 'Corto plazo',
  medio_plazo: 'Mediano plazo',
  largo_plazo: 'Largo plazo',
}

export const ETIQUETA_PRIORIDAD_RICE: Record<PrioridadRice, string> = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
}

export interface RiceEvaluacionRequest {
  area: string
  lider_funcional: string
  paises: number
  presupuesto_rango: PresupuestoRango
  impacta_plan_estrategico: boolean
  alcance_departamentos: number
  impacto: NivelImpactoConfianza
  confianza: NivelImpactoConfianza
  esfuerzo: NivelEsfuerzo
}

export interface RiceEvaluacion extends RiceEvaluacionRequest {
  id: number
  comite_idea_id: number
  calificacion: number
  prioridad: PrioridadRice
  completado_por_id: number
  completado_en: string
}
