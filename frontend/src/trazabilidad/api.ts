import { apiGet } from '../core/api'
import type { FlowControlIdea } from './types'

export function obtenerFlowControl(): Promise<FlowControlIdea[]> {
  return apiGet<FlowControlIdea[]>('/trazabilidad/flow-control')
}
