export type TipoDocumento = 'charter' | 'bpmn' | 'onepager' | 'raci' | 'bmc' | 'business_case'

export interface DocumentoGenerado {
  id: number
  idea_id: number
  tipo_documento: TipoDocumento
  contenido: Record<string, unknown>
  generado_en: string
}

export const ETIQUETA_TIPO_DOCUMENTO: Record<TipoDocumento, string> = {
  charter: 'Project Charter',
  bpmn: 'BPMN (as-is/to-be)',
  onepager: 'One-pager',
  raci: 'RACI',
  bmc: 'Business Model Canvas',
  business_case: 'Business Case',
}

export const ORDEN_TIPOS_DOCUMENTO: TipoDocumento[] = [
  'charter',
  'bpmn',
  'onepager',
  'raci',
  'bmc',
  'business_case',
]

export interface PendientesDocumentos {
  generados: TipoDocumento[]
  pendientes: TipoDocumento[]
  puede_generar: boolean
  documentos_desactualizados: boolean
}
