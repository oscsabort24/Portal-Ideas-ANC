import { useEffect, useState } from 'react'
import { listarDepartamentos } from '../../usuarios/api'
import type { Departamento } from '../../usuarios/types'
import { obtenerFlowControl } from '../api'
import type { FlowControlIdea } from '../types'
import DiagramaFlowControl from './DiagramaFlowControl'
import MatrizFlowControl from './MatrizFlowControl'
import PipelineFlowControl from './PipelineFlowControl'

type Tab = 'matriz' | 'visual' | 'como-funciona'

export default function FlowControlView() {
  const [tab, setTab] = useState<Tab>('visual')
  const [ideas, setIdeas] = useState<FlowControlIdea[] | null>(null)
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Filtros de la vista "Visual" — 100% client-side, GET /trazabilidad ya
  // trae departamento_id y dias_en_etapa por idea.
  const [filtroDepartamentoId, setFiltroDepartamentoId] = useState<number | 'todos'>('todos')
  const [filtroDiasMin, setFiltroDiasMin] = useState('')

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    setError(null)
    Promise.all([obtenerFlowControl(), listarDepartamentos()])
      .then(([datosIdeas, datosDepartamentos]) => {
        if (cancelado) return
        setIdeas(datosIdeas)
        setDepartamentos(datosDepartamentos)
      })
      .catch((err) => {
        if (!cancelado) setError(err instanceof Error ? err.message : 'No se pudo cargar Flow Control')
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [])

  // Filtro de umbral (mínimo), no de fecha exacta — pensado para aislar
  // cuellos de botella ("más de N días en su etapa"), no una franja de
  // calendario.
  const ideasFiltradas = ideas?.filter((idea) => {
    if (filtroDepartamentoId !== 'todos' && idea.departamento_id !== filtroDepartamentoId) return false
    const diasMin = Number(filtroDiasMin)
    if (filtroDiasMin && idea.dias_en_etapa <= diasMin) return false
    return true
  }) ?? null

  return (
    <div>
      <h1 className="page-title">Flow Control</h1>

      <div className="tabs-row">
        <button className={`tab-button ${tab === 'matriz' ? 'active' : ''}`} onClick={() => setTab('matriz')}>
          Matriz
        </button>
        <button className={`tab-button ${tab === 'visual' ? 'active' : ''}`} onClick={() => setTab('visual')}>
          Visual
        </button>
        <button className={`tab-button ${tab === 'como-funciona' ? 'active' : ''}`} onClick={() => setTab('como-funciona')}>
          Cómo funciona
        </button>
      </div>

      {tab === 'como-funciona' ? (
        <div className="tab-content">
          <DiagramaFlowControl />
        </div>
      ) : (
        <>
          {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando...</p>}
          {error && <p className="form-error">{error}</p>}

          {!cargando && !error && ideas && (
            <div className="tab-content">
              {tab === 'matriz' && <MatrizFlowControl ideas={ideas} departamentos={departamentos} />}
              {tab === 'visual' && (
                <>
                  <div className="form-row" style={{ marginBottom: 16 }}>
                    <div className="form-field">
                      <label className="form-label" htmlFor="flow-filtro-departamento">Departamento</label>
                      <select
                        id="flow-filtro-departamento"
                        className="form-input"
                        value={filtroDepartamentoId}
                        onChange={(e) =>
                          setFiltroDepartamentoId(e.target.value === 'todos' ? 'todos' : Number(e.target.value))
                        }
                      >
                        <option value="todos">Todos los departamentos</option>
                        {departamentos.map((d) => (
                          <option key={d.id} value={d.id}>{d.nombre}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-field">
                      <label className="form-label" htmlFor="flow-filtro-dias">Más de (días en etapa)</label>
                      <input
                        id="flow-filtro-dias"
                        type="number"
                        min={0}
                        className="form-input"
                        value={filtroDiasMin}
                        onChange={(e) => setFiltroDiasMin(e.target.value)}
                        placeholder="Sin filtro"
                      />
                    </div>
                  </div>
                  <PipelineFlowControl ideas={ideasFiltradas ?? []} />
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
