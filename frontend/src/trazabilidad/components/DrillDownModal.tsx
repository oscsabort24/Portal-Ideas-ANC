import { useEffect } from 'react'
import { FiX } from 'react-icons/fi'
import { ETIQUETA_ESTADO_FLOW } from '../estadosFlow'
import type { FlowControlIdea } from '../types'

export default function DrillDownModal({
  titulo,
  ideas,
  onCerrar,
}: {
  titulo: string
  ideas: FlowControlIdea[]
  onCerrar: () => void
}) {
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onCerrar])

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCerrar()
  }

  return (
    <div className="flow-drill-overlay" onClick={handleOverlayClick} role="dialog" aria-modal="true">
      <div className="flow-drill-modal">
        <div className="flow-drill-header">
          <span className="flow-drill-titulo">{titulo}</span>
          <button className="flow-drill-cerrar" onClick={onCerrar} aria-label="Cerrar">
            <FiX />
          </button>
        </div>

        <div className="flow-drill-body">
          {ideas.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>No hay ideas en esta celda.</p>
          ) : (
            ideas.map((idea) => (
              <div key={idea.idea_id} className="flow-drill-idea">
                <div className="flow-drill-idea-titulo">{idea.titulo}</div>
                <div className="flow-drill-idea-meta">
                  <span>{ETIQUETA_ESTADO_FLOW[idea.estado_flow]}</span>
                  <span>
                    · {idea.dias_en_etapa} día{idea.dias_en_etapa === 1 ? '' : 's'} en esta etapa
                  </span>
                </div>
                <div className="flow-drill-idea-personas">
                  <span>Autor: {idea.autor.nombre}</span>
                  {idea.revisor && <span>Revisor: {idea.revisor.nombre}</span>}
                  {idea.miembros_comite && idea.miembros_comite.length > 0 && (
                    <span>Comité: {idea.miembros_comite.map((m) => m.nombre).join(', ')}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
