import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiFileText, FiCheckCircle } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { listarIdeas } from '../api'
import type { Idea } from '../types'

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function MisIdeas() {
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const usuario = useUsuarioActual()
  const navigate = useNavigate()

  useEffect(() => {
    listarIdeas({ autor_id: usuario.id })
      .then(setIdeas)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las ideas'))
      .finally(() => setCargando(false))
  }, [usuario.id])

  if (cargando) return <p>Cargando...</p>
  if (error) return <p style={{ color: 'var(--error)' }}>{error}</p>

  return (
    <div>
      <h1 className="page-title">Mis ideas</h1>
      {ideas.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Todavía no has capturado ninguna idea.</p>}
      {ideas.map((idea) => (
        <div
          key={idea.id}
          className={`idea-card idea-card-${idea.estado}`}
          data-clickable="true"
          onClick={() => navigate(`/ideas/${idea.id}`)}
        >
          <div className="idea-card-header">
            <div className="idea-card-title-row">
              {idea.estado === 'enviada' ? (
                <FiCheckCircle className="idea-card-icon idea-card-icon-enviada" />
              ) : (
                <FiFileText className="idea-card-icon idea-card-icon-borrador" />
              )}
              <div>
                <div className="idea-card-title">{idea.titulo}</div>
                <div className="idea-card-date">Creada el {formatearFecha(idea.fecha_creacion)}</div>
              </div>
            </div>
            <span className={`idea-estado-badge ${idea.estado}`}>{idea.estado}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
