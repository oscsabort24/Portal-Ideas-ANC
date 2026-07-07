import { useState, type FormEvent } from 'react'
import { crearDepartamento } from '../api'
import type { Departamento } from '../types'

export default function FormularioDepartamento({ onCreado }: { onCreado: (dep: Departamento) => void }) {
  const [nombre, setNombre] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nombre.trim()) return

    setEnviando(true)
    setError(null)
    try {
      const dep = await crearDepartamento({ nombre: nombre.trim() })
      onCreado(dep)
      setNombre('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el departamento')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card form-card-inline" onSubmit={handleSubmit}>
      <div className="form-field form-field-grow">
        <label className="form-label" htmlFor="nombreDepartamento">Nombre del departamento</label>
        <input
          id="nombreDepartamento"
          className="form-input"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. Tecnología"
        />
      </div>
      {error && <p className="form-error">{error}</p>}
      <button type="submit" className="btn-primary" disabled={!nombre.trim() || enviando}>
        {enviando ? 'Creando...' : 'Agregar departamento'}
      </button>
    </form>
  )
}
