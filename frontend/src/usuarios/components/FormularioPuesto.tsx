import { useState, type FormEvent } from 'react'
import { crearPuesto } from '../api'
import type { Departamento, Puesto } from '../types'

export default function FormularioPuesto({
  departamentos,
  onCreado,
}: {
  departamentos: Departamento[]
  onCreado: (puesto: Puesto) => void
}) {
  const [nombre, setNombre] = useState('')
  const [departamentoId, setDepartamentoId] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nombre.trim() || !departamentoId) return

    setEnviando(true)
    setError(null)
    try {
      const puesto = await crearPuesto({ nombre: nombre.trim(), departamento_id: Number(departamentoId) })
      onCreado(puesto)
      setNombre('')
      setDepartamentoId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el puesto')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card form-card-inline" onSubmit={handleSubmit}>
      <div className="form-field form-field-grow">
        <label className="form-label" htmlFor="nombrePuesto">Nombre del puesto</label>
        <input
          id="nombrePuesto"
          className="form-input"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. Jefe de Mantenimiento"
        />
      </div>
      <div className="form-field form-field-grow">
        <label className="form-label" htmlFor="departamentoPuesto">Departamento</label>
        <select
          id="departamentoPuesto"
          className="form-input"
          value={departamentoId}
          onChange={(e) => setDepartamentoId(e.target.value)}
        >
          <option value="">Selecciona un departamento</option>
          {departamentos.map((d) => (
            <option key={d.id} value={d.id}>{d.nombre}</option>
          ))}
        </select>
      </div>
      {error && <p className="form-error">{error}</p>}
      <button type="submit" className="btn-primary" disabled={!nombre.trim() || !departamentoId || enviando}>
        {enviando ? 'Creando...' : 'Agregar puesto'}
      </button>
    </form>
  )
}
