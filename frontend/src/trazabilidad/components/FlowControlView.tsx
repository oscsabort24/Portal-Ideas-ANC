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
              {tab === 'visual' && <PipelineFlowControl ideas={ideas} />}
            </div>
          )}
        </>
      )}
    </div>
  )
}
