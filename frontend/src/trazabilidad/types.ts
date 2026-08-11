export type EstadoFlow =
  | 'borrador'
  | 'revision_pendiente_asignacion'
  | 'revision_en_curso'
  | 'revision_cambios_solicitados'
  | 'clasificacion_pendiente'
  | 'comite_en_cola'
  | 'comite_rechazada'
  | 'comite_aprobada_sin_documentos'
  | 'documentos_en_generacion'
  | 'documentos_completos'

export interface PersonaResumen {
  id: number
  nombre: string
}

export interface FlowControlIdea {
  idea_id: number
  titulo: string
  estado_flow: EstadoFlow
  departamento_id: number | null
  departamento_nombre: string | null
  autor: PersonaResumen
  revisor: PersonaResumen | null
  miembros_comite: PersonaResumen[] | null
  fecha_entrada_etapa: string
  dias_en_etapa: number
}
