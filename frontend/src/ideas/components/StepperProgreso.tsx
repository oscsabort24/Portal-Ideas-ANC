import {
  ACCION_POR_ESTADO,
  ETIQUETA_ESTADO_FLOW,
  PASOS_PROGRESO,
  PROGRESO_POR_ESTADO,
} from '../../trazabilidad/estadosFlow'
import type { EstadoFlow } from '../../trazabilidad/types'

/** Estado visual de un círculo del stepper. */
type EstadoPaso = 'completado' | 'actual' | 'accion' | 'rechazo' | 'pendiente' | 'cancelado'

function estadoDelPaso(indice: number, paso: number, tipo: string): EstadoPaso {
  const numero = indice + 1
  if (paso === 0) return 'pendiente'
  if (numero < paso) return 'completado'
  if (numero === paso) {
    if (tipo === 'rechazo') return 'rechazo'
    if (tipo === 'accion') return 'accion'
    if (tipo === 'completo') return 'completado'
    return 'actual'
  }
  // Después del paso actual. Tras un rechazo NO son "pendientes": pendiente
  // comunica "va a pasar", y acá no va a pasar nunca.
  return tipo === 'rechazo' ? 'cancelado' : 'pendiente'
}

const ICONO: Record<EstadoPaso, string> = {
  completado: '✓',
  actual: '',
  accion: '!',
  rechazo: '✕',
  pendiente: '',
  cancelado: '',
}

/**
 * Stepper de 5 pasos para el detalle de la idea.
 *
 * El paso actual cambia de COLOR e ÍCONO, nunca de posición: "cambios
 * solicitados" no retrocede el stepper porque en el modelo de datos la idea
 * nunca salió del paso 2 — el ida y vuelta ocurre dentro del paso, no entre
 * pasos (ver trazabilidad/service.py:_derivar_estado).
 */
export default function StepperProgreso({ estadoFlow }: { estadoFlow: EstadoFlow | null }) {
  if (!estadoFlow) return null

  const { paso, tipo } = PROGRESO_POR_ESTADO[estadoFlow]
  const accion = ACCION_POR_ESTADO[estadoFlow]

  return (
    <div className="stepper" role="group" aria-label="Progreso de la idea">
      <ol className="stepper-pasos">
        {PASOS_PROGRESO.map((nombre, i) => {
          const estado = estadoDelPaso(i, paso, tipo)
          const esActual = i + 1 === paso
          return (
            <li
              key={nombre}
              className={`stepper-paso stepper-paso-${estado}`}
              aria-current={esActual ? 'step' : undefined}
            >
              <span className="stepper-circulo" aria-hidden="true">
                {ICONO[estado] || i + 1}
              </span>
              <span className="stepper-etiqueta">{nombre}</span>
            </li>
          )
        })}
      </ol>

      <p className={`stepper-detalle stepper-detalle-${tipo}`}>
        <strong>{ETIQUETA_ESTADO_FLOW[estadoFlow]}</strong>
        {accion && <span> — {accion}</span>}
      </p>
    </div>
  )
}
