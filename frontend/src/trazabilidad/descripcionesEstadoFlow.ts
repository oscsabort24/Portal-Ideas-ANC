import type { EstadoFlow } from './types'

// Texto corto y estático para la pestaña "Cómo funciona" — puramente
// explicativo, no depende de ningún dato real.
export const DESCRIPCION_ESTADO_FLOW: Record<EstadoFlow, string> = {
  borrador: 'El autor conversa con la IA para documentar la idea.',
  revision_pendiente_asignacion: 'Se asigna un encargado de área, automático o a mano.',
  revision_en_curso: 'El revisor aprueba, pide cambios o reasigna.',
  revision_cambios_solicitados: 'El autor ajusta la idea con la retroalimentación recibida.',
  clasificacion_pendiente: 'Se clasifica como Innovación o Transformación Digital.',
  comite_en_cola: 'Espera turno para que el comité (CAB) la revise.',
  comite_rechazada: 'El comité decide no avanzar con la idea.',
  comite_aprobada_sin_documentos: 'El comité aprobó; los documentos formales aún no existen.',
  documentos_en_generacion: 'Algunos de los 6 documentos formales ya se generaron.',
  documentos_completos: 'Los 6 documentos formales están listos.',
}
