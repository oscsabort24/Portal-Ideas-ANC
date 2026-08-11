import { useMemo, useState } from 'react'
import type { Departamento } from '../../usuarios/types'
import { ETIQUETA_ESTADO_FLOW, ORDEN_ESTADOS_FLOW } from '../estadosFlow'
import type { EstadoFlow, FlowControlIdea } from '../types'
import DrillDownModal from './DrillDownModal'

const SIN_DEPARTAMENTO_ID = -1

function colorCelda(cantidad: number): string {
  if (cantidad === 0) return 'var(--surface-2)'
  if (cantidad === 1) return 'var(--primary-faint)'
  if (cantidad <= 3) return '#a9c9ec'
  if (cantidad <= 6) return '#5a9bdb'
  return 'var(--primary)'
}

function colorTexto(cantidad: number): string {
  return cantidad > 6 ? '#fff' : 'var(--text)'
}

interface CeldaSeleccionada {
  departamentoId: number
  estado: EstadoFlow
}

export default function MatrizFlowControl({
  ideas,
  departamentos,
}: {
  ideas: FlowControlIdea[]
  departamentos: Departamento[]
}) {
  const [celdaSeleccionada, setCeldaSeleccionada] = useState<CeldaSeleccionada | null>(null)

  const filas = useMemo(
    () => [...departamentos.map((d) => ({ id: d.id, nombre: d.nombre })), { id: SIN_DEPARTAMENTO_ID, nombre: 'Sin departamento' }],
    [departamentos],
  )

  const conteos = useMemo(() => {
    const mapa = new Map<string, number>()
    for (const idea of ideas) {
      const deptoId = idea.departamento_id ?? SIN_DEPARTAMENTO_ID
      const clave = `${deptoId}::${idea.estado_flow}`
      mapa.set(clave, (mapa.get(clave) ?? 0) + 1)
    }
    return mapa
  }, [ideas])

  const ideasDeLaCelda = useMemo(() => {
    if (!celdaSeleccionada) return []
    return ideas.filter(
      (idea) =>
        (idea.departamento_id ?? SIN_DEPARTAMENTO_ID) === celdaSeleccionada.departamentoId &&
        idea.estado_flow === celdaSeleccionada.estado,
    )
  }, [ideas, celdaSeleccionada])

  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table className="flow-matriz">
          <thead>
            <tr>
              <th className="flow-matriz-th-depto">Departamento</th>
              {ORDEN_ESTADOS_FLOW.map((estado) => (
                <th key={estado} className="flow-matriz-th-estado">
                  {ETIQUETA_ESTADO_FLOW[estado]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filas.map((depto) => (
              <tr key={depto.id}>
                <td className="flow-matriz-td-depto">{depto.nombre}</td>
                {ORDEN_ESTADOS_FLOW.map((estado) => {
                  const cantidad = conteos.get(`${depto.id}::${estado}`) ?? 0
                  return (
                    <td
                      key={estado}
                      className="flow-matriz-celda"
                      style={{
                        background: colorCelda(cantidad),
                        color: colorTexto(cantidad),
                        cursor: cantidad > 0 ? 'pointer' : 'default',
                      }}
                      onClick={() => cantidad > 0 && setCeldaSeleccionada({ departamentoId: depto.id, estado })}
                    >
                      {cantidad || ''}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {celdaSeleccionada && (
        <DrillDownModal
          titulo={`${filas.find((d) => d.id === celdaSeleccionada.departamentoId)?.nombre ?? ''} — ${ETIQUETA_ESTADO_FLOW[celdaSeleccionada.estado]}`}
          ideas={ideasDeLaCelda}
          onCerrar={() => setCeldaSeleccionada(null)}
        />
      )}
    </>
  )
}
