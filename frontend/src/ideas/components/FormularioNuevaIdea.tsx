import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiFileText } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { crearIdea, listarIdeas } from '../api'
import type { Idea } from '../types'

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function FormularioNuevaIdea() {
  const [titulo, setTitulo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [borradores, setBorradores] = useState<Idea[]>([])
  const usuario = useUsuarioActual()
  const navigate = useNavigate()

  useEffect(() => {
    listarIdeas({ autor_id: usuario.id, estado: 'borrador' })
      .then(setBorradores)
      .catch(() => setBorradores([]))
  }, [usuario.id])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!titulo.trim()) return

    setEnviando(true)
    setError(null)
    try {
      const idea = await crearIdea({ titulo: titulo.trim(), autor_id: usuario.id })
      navigate(`/ideas/${idea.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear la idea')
      setEnviando(false)
    }
  }

  return (
    <div className="page-nueva-idea">
      <h1 className="page-title">Nueva idea</h1>
      <form className="form-nueva-idea" onSubmit={handleSubmit}>
        <div className="form-field">
          <label className="form-label" htmlFor="titulo">
            Título de la idea
          </label>
          <input
            id="titulo"
            className="form-input"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ej. Automatizar la conciliación de facturas"
            autoFocus
          />
        </div>
        {error && <p style={{ color: 'var(--error)', fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <button type="submit" className="btn-primary" disabled={!titulo.trim() || enviando}>
          {enviando ? 'Creando...' : 'Comenzar entrevista'}
        </button>
      </form>

      {borradores.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h2 className="page-title" style={{ fontSize: 16, marginBottom: 12 }}>
            Tus borradores
          </h2>
          {borradores.map((idea) => (
            <div
              key={idea.id}
              className="idea-card idea-card-borrador"
              data-clickable="true"
              onClick={() => navigate(`/ideas/${idea.id}`)}
            >
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiFileText className="idea-card-icon idea-card-icon-borrador" />
                  <div>
                    <div className="idea-card-title">{idea.titulo}</div>
                    <div className="idea-card-date">Creada el {formatearFecha(idea.fecha_creacion)}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
