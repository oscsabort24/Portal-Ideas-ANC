import type { EstadoFlow } from './types'

// Mismo orden que trazabilidad/service.py:ESTADOS_FLOW en el backend — las
// columnas de la matriz y los nodos del pipeline siguen este orden.
export const ORDEN_ESTADOS_FLOW: EstadoFlow[] = [
  'borrador',
  'revision_pendiente_asignacion',
  'revision_en_curso',
  'revision_cambios_solicitados',
  'revision_rechazada',
  'clasificacion_pendiente',
  'comite_en_cola',
  'comite_rechazada',
  'comite_aprobada_sin_documentos',
  'documentos_en_generacion',
  'documentos_completos',
]

export const ETIQUETA_ESTADO_FLOW: Record<EstadoFlow, string> = {
  borrador: 'Borrador',
  revision_pendiente_asignacion: 'Rev. sin asignar',
  revision_en_curso: 'En revisión',
  revision_cambios_solicitados: 'Cambios solicitados',
  revision_rechazada: 'Rechazada en revisión',
  clasificacion_pendiente: 'Pend. clasificación',
  comite_en_cola: 'En cola de comité',
  comite_rechazada: 'Rechazada',
  comite_aprobada_sin_documentos: 'Aprobada, sin docs.',
  documentos_en_generacion: 'Docs. en generación',
  documentos_completos: 'Docs. completos',
}
