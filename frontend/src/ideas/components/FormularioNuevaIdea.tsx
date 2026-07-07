import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { crearIdea } from '../api'

export default function FormularioNuevaIdea() {
  const [titulo, setTitulo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const usuario = useUsuarioActual()
  const navigate = useNavigate()

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
    </div>
  )
}
