import { useEffect, useMemo, useRef, useState } from 'react'
import { FiChevronRight } from 'react-icons/fi'
import { ETIQUETA_ESTADO_FLOW, ORDEN_ESTADOS_FLOW } from '../estadosFlow'
import type { EstadoFlow, FlowControlIdea } from '../types'
import DrillDownModal from './DrillDownModal'

type ColorLed = 'verde' | 'ambar' | 'rojo'

function colorLedDeIdeas(ideasDelEstado: FlowControlIdea[]): ColorLed {
  if (ideasDelEstado.length === 0) return 'verde'
  const maxDias = Math.max(...ideasDelEstado.map((i) => i.dias_en_etapa))
  if (maxDias <= 0) return 'verde'
  if (maxDias <= 7) return 'ambar'
  return 'rojo'
}

/**
 * Con flex-wrap, cada tarjeta lleva su conector (línea + flecha) pegado a
 * su propio lado derecho. Cuando el wrap corta la fila justo después de
 * una tarjeta, ese conector queda apuntando al vacío — no hay tarjeta
 * siguiente en la misma fila (se ve como un punto/línea suelta flotando
 * entre una fila y la otra). Para evitarlo, medimos en runtime la
 * posición vertical (`offsetTop`) de cada tarjeta: si la siguiente tarjeta
 * quedó en otra fila (o no hay siguiente), esta es la última de su fila y
 * no debe dibujar conector.
 */
function useUltimosEnFila(cantidadNodos: number, dependencias: unknown[]): {
  nodoRefs: React.MutableRefObject<(HTMLDivElement | null)[]>
  esUltimoEnFila: (indice: number) => boolean
} {
  const nodoRefs = useRef<(HTMLDivElement | null)[]>([])
  const [ultimos, setUltimos] = useState<Set<number>>(new Set())

  useEffect(() => {
    function recalcular() {
      const tops = nodoRefs.current.map((el) => el?.offsetTop ?? 0)
      const siguienteUltimos = new Set<number>()
      for (let i = 0; i < tops.length; i++) {
        const esUltimoAbsoluto = i === tops.length - 1
        const siguienteEnOtraFila = !esUltimoAbsoluto && tops[i + 1] !== tops[i]
        if (esUltimoAbsoluto || siguienteEnOtraFila) siguienteUltimos.add(i)
      }
      setUltimos(siguienteUltimos)
    }

    recalcular()
    window.addEventListener('resize', recalcular)
    return () => window.removeEventListener('resize', recalcular)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cantidadNodos, ...dependencias])

  return { nodoRefs, esUltimoEnFila: (indice: number) => ultimos.has(indice) }
}

export default function PipelineFlowControl({ ideas }: { ideas: FlowControlIdea[] }) {
  const [estadoSeleccionado, setEstadoSeleccionado] = useState<EstadoFlow | null>(null)

  const porEstado = useMemo(() => {
    const mapa = new Map<EstadoFlow, FlowControlIdea[]>()
    for (const estado of ORDEN_ESTADOS_FLOW) mapa.set(estado, [])
    for (const idea of ideas) {
      mapa.get(idea.estado_flow)?.push(idea)
    }
    return mapa
  }, [ideas])

  const { nodoRefs, esUltimoEnFila } = useUltimosEnFila(ORDEN_ESTADOS_FLOW.length, [ideas])

  return (
    <>
      <div className="flow-pipeline">
        {ORDEN_ESTADOS_FLOW.map((estado, indice) => {
          const ideasDelEstado = porEstado.get(estado) ?? []
          const led = colorLedDeIdeas(ideasDelEstado)
          const clickeable = ideasDelEstado.length > 0

          return (
            <div className="flow-pipeline-item" key={estado}>
              <div
                ref={(el) => (nodoRefs.current[indice] = el)}
                className={`flow-pipeline-nodo flow-pipeline-nodo--${led} ${clickeable ? 'flow-pipeline-nodo--clickeable' : ''}`}
                onClick={() => clickeable && setEstadoSeleccionado(estado)}
              >
                <span className={`flow-pipeline-led flow-pipeline-led--${led}`} />
                <div className="flow-pipeline-numero">{ideasDelEstado.length}</div>
                <div className="flow-pipeline-etiqueta">{ETIQUETA_ESTADO_FLOW[estado]}</div>
              </div>

              {!esUltimoEnFila(indice) && (
                <div className="flow-pipeline-conector" aria-hidden="true">
                  <span className="flow-pipeline-conector-linea" />
                  <FiChevronRight className="flow-pipeline-conector-flecha" />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {estadoSeleccionado && (
        <DrillDownModal
          titulo={ETIQUETA_ESTADO_FLOW[estadoSeleccionado]}
          ideas={porEstado.get(estadoSeleccionado) ?? []}
          onCerrar={() => setEstadoSeleccionado(null)}
        />
      )}
    </>
  )
}
