import { PASOS_PROGRESO, PROGRESO_POR_ESTADO } from '../../trazabilidad/estadosFlow'
import type { EstadoFlow } from '../../trazabilidad/types'

/**
 * Versión compacta del stepper para cada fila de "Mis ideas".
 *
 * Deliberadamente NO es un stepper: cinco círculos con etiquetas en cada fila
 * de una lista es ruido. Son 5 segmentos que reusan exactamente la misma
 * paleta y el mismo mapeo (PROGRESO_POR_ESTADO), así que la barra de la lista
 * y el stepper del detalle no pueden contradecirse.
 */
export default function MiniProgreso({ estadoFlow }: { estadoFlow: EstadoFlow | null }) {
  if (!estadoFlow) return null

  const { paso, tipo } = PROGRESO_POR_ESTADO[estadoFlow]

  return (
    <div
      className="mini-progreso"
      role="img"
      aria-label={`Paso ${paso} de ${PASOS_PROGRESO.length}: ${PASOS_PROGRESO[Math.max(0, paso - 1)]}`}
      title={PASOS_PROGRESO.map((n, i) => `${i + 1}. ${n}`).join('\n')}
    >
      {PASOS_PROGRESO.map((nombre, i) => {
        const numero = i + 1
        let estado: string
        if (paso === 0) estado = 'pendiente'
        else if (numero < paso) estado = 'completado'
        else if (numero === paso) estado = tipo === 'completo' ? 'completado' : tipo
        else estado = tipo === 'rechazo' ? 'cancelado' : 'pendiente'
        return <span key={nombre} className={`mini-progreso-seg mini-progreso-${estado}`} />
      })}
    </div>
  )
}
